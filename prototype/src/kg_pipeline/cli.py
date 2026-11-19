"""Příkazová řádka; lokální validace a plán nevyžadují databázi ani LLM."""

import argparse
import json
import os
import sys
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import ValidationError

from kg_pipeline.graph import build_plan, import_plan
from kg_pipeline.ingestion import load_dataset
from kg_pipeline.ontology import registry_dict
from kg_pipeline.schema import Dataset
from kg_pipeline.extraction.config import load_config
from kg_pipeline.extraction.ollama import OllamaClient, OllamaError
from kg_pipeline.extraction.pipeline import check_inventory, run_pipeline
from kg_pipeline.extraction.runner import write_json

QUERY_NAMES = ("acquisitions", "cross_document", "provenance", "counts")


def emit(data: object, output: Path | None = None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if output is None:
        print(text, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        # Auditní soubory nepřepisujeme omylem při opakovaném běhu.
        with output.open("x", encoding="utf-8") as handle:
            handle.write(text)


def connection_settings() -> tuple[str, str, str, str]:
    password = os.environ.get("NEO4J_PASSWORD", "")
    if not password:
        raise ValueError("Doplň NEO4J_PASSWORD do lokálního .env nebo prostředí.")
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    parsed = urlsplit(uri)
    if parsed.scheme not in {"bolt", "bolt+s", "bolt+ssc", "neo4j", "neo4j+s", "neo4j+ssc"} or not parsed.hostname:
        raise ValueError("NEO4J_URI musí být platná Bolt/Neo4j adresa.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Přihlašovací údaje nepatří do NEO4J_URI; použij proměnné prostředí.")
    return uri, os.environ.get("NEO4J_USER", "neo4j"), password, os.environ.get("NEO4J_DATABASE", "neo4j")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validace a import referenčního znalostního grafu.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("schema", "registry"):
        command = subparsers.add_parser(name)
        command.add_argument("--output", type=Path)
    for name in ("validate", "plan", "import", "query"):
        command = subparsers.add_parser(name)
        command.add_argument("dataset", type=Path, help="Cesta k referenčnímu JSON.")
        if name in {"import", "query"}:
            command.add_argument("--env-file", type=Path)
        if name == "query":
            command.add_argument("name", choices=QUERY_NAMES)
        if name == "plan":
            command.add_argument("--output", type=Path)
    doctor = subparsers.add_parser("doctor", help="Ověří lokální Ollama a modely jednotlivých rolí.")
    doctor.add_argument("--config", type=Path, default=Path("pipeline.toml"))
    run = subparsers.add_parser("run", help="Automaticky zpracuje texty několika lokálními modelovými kroky.")
    run.add_argument("manifest", type=Path)
    run.add_argument("--config", type=Path, default=Path("pipeline.toml"))
    run.add_argument("--output", type=Path, help="Nová složka pro výstupy a audit; nesmí již existovat.")
    run.add_argument("--import", dest="import_graph", action="store_true", help="Po extrakci importuje přijaté informace do Neo4j.")
    run.add_argument("--env-file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            emit(Dataset.model_json_schema(), args.output)
            return 0
        if args.command == "registry":
            emit(registry_dict(), args.output)
            return 0
        if args.command == "doctor":
            config = load_config(args.config)
            inventory = OllamaClient(config).inventory()
            emit({"ready": True, "server": inventory["server"], "models": check_inventory(inventory, config)})
            return 0
        if args.command == "run":
            if args.env_file and not args.env_file.is_file():
                raise ValueError("Zadaný konfigurační soubor neexistuje.")
            summary = run_pipeline(args.manifest, args.config, args.output,
                                   progress=lambda message: print(message, file=sys.stderr, flush=True))
            if args.import_graph:
                if summary["accepted_events"] == 0:
                    summary["graph_import"] = {"status": "skipped_no_accepted_events"}
                else:
                    try:
                        load_dotenv(args.env_file or Path.cwd() / ".env", override=False)
                        uri, user, password, database = connection_settings()
                        with GraphDatabase.driver(uri, auth=(user, password), connection_timeout=5) as driver:
                            driver.verify_connectivity()
                            imported = import_plan(driver, database, build_plan(load_dataset(Path(summary["dataset"]))))
                        summary["graph_import"] = {"status": "complete", **imported}
                    except (DriverError, Neo4jError, OSError, ValueError) as exc:
                        write_json(Path(summary["output"]) / "import.json",
                                   {"status": "failed", "error_type": type(exc).__name__})
                        raise
                write_json(Path(summary["output"]) / "import.json", summary["graph_import"])
            emit(summary)
            return 0
        loaded = load_dataset(args.dataset)
        plan = build_plan(loaded)
        if args.command == "validate":
            emit({"valid": True, "dataset_id": loaded.dataset.dataset_id,
                  "dataset_version": loaded.dataset.dataset_version,
                  "documents": len(loaded.dataset.documents), "fingerprint": loaded.fingerprint,
                  "planned_nodes": len(plan.nodes), "planned_edges": len(plan.edges),
                  "candidates": sum(len(d.candidates) for d in loaded.dataset.documents)})
        elif args.command == "plan":
            emit(plan.as_dict(), args.output)
        else:
            env_file = args.env_file or Path.cwd() / ".env"
            if args.env_file and not env_file.is_file():
                raise ValueError("Zadaný konfigurační soubor neexistuje.")
            load_dotenv(env_file, override=False)
            uri, user, password, database = connection_settings()
            with GraphDatabase.driver(uri, auth=(user, password), connection_timeout=5) as driver:
                driver.verify_connectivity()
                if args.command == "import":
                    emit({"import_id": plan.import_id, **import_plan(driver, database, plan)})
                else:
                    query = files("kg_pipeline").joinpath("queries", args.name + ".cypher").read_text(encoding="utf-8")
                    with driver.session(database=database) as session:
                        records = session.execute_read(lambda tx: tx.run(query, import_id=plan.import_id).data())
                    emit(records)
        return 0
    except ValidationError as exc:
        errors = [{"path": ".".join(map(str, e["loc"])), "message": e["msg"]}
                  for e in exc.errors(include_input=False, include_url=False)]
        print(json.dumps({"error": "Nevalidní meziformát", "details": errors}, ensure_ascii=False), file=sys.stderr)
    except (DriverError, Neo4jError):
        # Zprávy driveru mohou obsahovat URI nebo údaje serveru; nezveřejňujeme je.
        print("Chyba Neo4j. Ověř běh databáze, připojení a přihlašovací údaje v .env.", file=sys.stderr)
    except OllamaError as exc:
        print(f"Chyba Ollama: {exc}", file=sys.stderr)
    except (OSError, ValueError) as exc:
        print(f"Chyba: {exc}", file=sys.stderr)
    return 1
