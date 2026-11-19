"""Explicitně zapínané testy; vytvářejí vlastní namespace, nic nemažou."""

import os
from importlib.resources import files
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase

from conftest import save_dataset
from kg_pipeline.cli import connection_settings
from kg_pipeline.graph import build_plan, import_plan
from kg_pipeline.ingestion import load_dataset

pytestmark = [pytest.mark.integration,
              pytest.mark.skipif(os.environ.get("KG_RUN_INTEGRATION") != "1",
                                 reason="Nastav KG_RUN_INTEGRATION=1 pro testy se skutečnou Neo4j.")]


@pytest.fixture
def database():
    load_dotenv(".env", override=False)
    uri, user, password, name = connection_settings()
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        yield driver, name


def query(driver, name, plan, query_name):
    cypher = files("kg_pipeline").joinpath("queries", query_name + ".cypher").read_text(encoding="utf-8")
    with driver.session(database=name) as session:
        return session.execute_read(lambda tx: tx.run(cypher, import_id=plan.import_id).data())


def test_real_import_idempotence_queries_and_provenance(database, dataset_path, raw_dataset):
    driver, name = database
    raw_dataset["dataset_version"] = "test-" + uuid4().hex
    save_dataset(dataset_path, raw_dataset)
    plan = build_plan(load_dataset(dataset_path))
    import_plan(driver, name, plan)
    before = query(driver, name, plan, "counts")
    repeated = import_plan(driver, name, plan)
    assert repeated["created_data_nodes"] == repeated["created_edges"] == 0
    assert query(driver, name, plan, "counts") == before == [{"nodes": len(plan.nodes), "edges": len(plan.edges)}]
    rows = query(driver, name, plan, "acquisitions")
    assert [(r["document"], r["buyer"], r["seller"], r["object"], r["year"], r["approximate"]) for r in rows] == [
        ("doc_001", "Matěj Kovář", "Václav Svoboda", "dům U Modré hvězdy v Brně", 1521, False),
        ("doc_002", "Anna Malá", "Matěj Kovář", "dům U Modré hvězdy v Brně", 1524, False),
        ("doc_003", "Matěj Kovář z Olomouce", "Jan Dlouhý", "zahrada", 1530, True),
    ]
    provenance = query(driver, name, plan, "provenance")
    assert len(provenance) == 3
    assert all(row["evidence"] == row["verified_text"] and row["synthetic"] for row in provenance)
    links = query(driver, name, plan, "cross_document")
    assert len(links) == 2
    assert all({r["document_a"], r["document_b"]} == {"doc_001", "doc_002"} for r in links)


def test_changed_input_is_refused_atomically(database, dataset_path, raw_dataset):
    driver, name = database
    raw_dataset["dataset_version"] = "test-" + uuid4().hex
    save_dataset(dataset_path, raw_dataset)
    original = build_plan(load_dataset(dataset_path))
    import_plan(driver, name, original)
    raw_dataset["documents"][0]["entities"][0]["label"] = "Nesmí přepsat původní uzel"
    save_dataset(dataset_path, raw_dataset)
    with pytest.raises(ValueError, match="jiná data"):
        import_plan(driver, name, build_plan(load_dataset(dataset_path)))
    assert query(driver, name, original, "acquisitions")[0]["buyer"] == "Matěj Kovář"
    assert query(driver, name, original, "counts") == [{"nodes": len(original.nodes), "edges": len(original.edges)}]


def test_pipeline_dataset_import_and_model_metadata(database, dataset_path, raw_dataset, tmp_path):
    from kg_pipeline.extraction.pipeline import run_pipeline
    from test_pipeline import FakeBackend

    config = tmp_path / "pipeline.toml"
    config.write_text("\n".join(f'[models.{role}]\nmodel = "{role}-model:local"\n'
                                for role in ("entities", "events", "review", "identity")))
    result = run_pipeline(dataset_path.parent / "input.json", config, tmp_path / "automatic", FakeBackend(raw_dataset))
    plan = build_plan(load_dataset(tmp_path / "automatic" / "dataset.json"))
    driver, name = database
    import_plan(driver, name, plan)
    assert len(query(driver, name, plan, "acquisitions")) == result["accepted_events"] == 3
    assert query(driver, name, plan, "cross_document") == []
    with driver.session(database=name) as session:
        marker = session.execute_read(lambda tx: tx.run(
            "MATCH (m:KGImport {id: $id}) RETURN m.extraction_method AS method, m.run_id AS run_id",
            id=plan.import_id,
        ).single().data())
    assert marker == {"method": "ollama_pipeline", "run_id": result["run_id"]}
