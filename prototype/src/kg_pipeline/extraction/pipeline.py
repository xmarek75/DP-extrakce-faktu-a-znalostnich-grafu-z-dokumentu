"""Sekvenční text → entity → události → revize → návrhy identit → graf."""

import hashlib
import json
import platform
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from kg_pipeline import __version__
from kg_pipeline.extraction import prompts
from kg_pipeline.extraction.config import PipelineConfig, load_config
from kg_pipeline.extraction.models import (
    DocumentReview, EntityExtraction, EventExtraction, IdentityResolution,
    InputDocument, InputManifest,
)
from kg_pipeline.extraction.ollama import ModelBackend, OllamaClient
from kg_pipeline.extraction.runner import StageRunner, write_json
from kg_pipeline.graph import build_plan
from kg_pipeline.ingestion import validate_dataset, verify_evidence
from kg_pipeline.ontology import registry_dict
from kg_pipeline.schema import (
    Dataset, Document, IdentityLink, REGISTRY_VERSION, RunProvenance, SCHEMA_VERSION, require_unique,
)

POLICY_VERSION = "model-review-v2"


def source_passages(text: str) -> list[str]:
    return list(dict.fromkeys(line.strip() for line in text.splitlines() if line.strip()))


def evidence_schema(response_model: type[BaseModel], text: str) -> dict:
    """Důkazy se vybírají z původních řádků; LLM je nemusí opisovat."""
    schema = response_model.model_json_schema()
    passages = source_passages(text)
    if passages:
        schema["$defs"]["Quote"]["properties"]["text"]["enum"] = passages
    else:
        schema["properties"]["evidence"]["maxItems"] = 0
    return schema


def check_evidence_choices(doc: Document, text: str) -> None:
    allowed = set(source_passages(text))
    for quote in doc.evidence:
        if quote.text not in allowed:
            raise ValueError(f"{doc.id}/{quote.local_id}: vyber celý povolený zdrojový úsek beze změn.")


def entity_document(source: InputDocument, result: EntityExtraction, text: str) -> Document:
    entities = []
    for entity in result.entities:
        value = entity.model_dump()
        value["label"] = " ".join(unicodedata.normalize("NFC", entity.label).split())
        entities.append(value)
    doc = Document.model_validate({**source.model_dump(), "entities": entities,
                                   "evidence": [e.model_dump() for e in result.evidence], "events": []})
    verify_evidence(doc, text)
    check_evidence_choices(doc, text)
    return doc


def event_document(doc: Document, result: EventExtraction, text: str) -> Document:
    evidence = {quote.local_id: quote.model_dump() for quote in doc.evidence}
    require_unique([quote.local_id for quote in result.evidence], "nové důkazy událostí")
    for quote in result.evidence:
        if quote.local_id in evidence and evidence[quote.local_id]["text"] != quote.text:
            raise ValueError("Model změnil obsah již existujícího důkazu.")
        if quote.local_id not in evidence:
            evidence[quote.local_id] = quote.model_dump()
    value = doc.model_dump()
    value.update(events=[e.model_dump() for e in result.events], evidence=list(evidence.values()),
                 candidates=[c.model_dump() for c in result.candidates])
    extracted = Document.model_validate(value)
    verify_evidence(extracted, text)
    check_evidence_choices(extracted, text)
    return extracted


def check_review(review: DocumentReview, doc: Document) -> None:
    for name in ("entities", "events"):
        decisions = getattr(review, name)
        require_unique([item.local_id for item in decisions], f"revize {name}")
        if {item.local_id for item in decisions} != {item.local_id for item in getattr(doc, name)}:
            raise ValueError(f"Revize musí obsahovat právě všechny záznamy {name}.")


def review_schema(doc: Document) -> dict:
    """Model dostane stejnou kardinalitu, jakou potom vyžaduje kontrola revize."""
    schema = DocumentReview.model_json_schema()
    for field, definition in (("entities", "ReviewDecision"), ("events", "EventReview")):
        records = getattr(doc, field)
        schema["properties"][field].update(minItems=len(records), maxItems=len(records))
        if records:
            schema["$defs"][definition]["properties"]["local_id"]["enum"] = [record.local_id for record in records]
    return schema


def review_context(doc: Document, text: str) -> dict:
    """Revizní model posuzuje obsah, nikoli dosavadní aplikační stavy kandidátů."""
    value = {"id": doc.id, "evidence": [quote.model_dump() for quote in doc.evidence]}
    for name in ("entities", "events"):
        value[name] = [item.model_dump(exclude={"status"}) for item in getattr(doc, name)]
    return {"text": text, "extraction": value, "registry": compact_registry()}


def apply_review(doc: Document, review: DocumentReview, acceptance: str) -> tuple[Document, dict]:
    check_review(review, doc)
    value = doc.model_dump()
    entity_decisions = {decision.local_id: decision for decision in review.entities}
    applied = {"entities": [], "events": []}
    for entity in value["entities"]:
        decision = entity_decisions[entity["local_id"]]
        entity["status"] = ("rejected" if decision.decision == "rejected" else
                            "accepted" if decision.decision == "supported" and acceptance == "model_review"
                            else "requires_review")
        applied["entities"].append({**decision.model_dump(), "status": entity["status"]})
    accepted_entities = {entity["local_id"] for entity in value["entities"] if entity["status"] == "accepted"}
    reviews = {decision.local_id: decision for decision in review.events}
    evidence = {quote.local_id: quote.text for quote in doc.evidence}
    for event in value["events"]:
        decision = reviews[event["local_id"]]
        gates = []
        if decision.decision != "supported":
            gates.append("review_not_supported")
        if not all((decision.roles_supported, decision.time_supported, decision.modality_preserved)):
            gates.append("review_checks_failed")
        if event["assertion"] != "affirmed":
            gates.append("non_affirmed_assertion")
        if event["acquirer"] is not None and event["acquirer"] == event["former_owner"]:
            gates.append("same_local_party_requires_review")
        participants = {event[key] for key in ("acquirer", "former_owner", "transferred_object") if event[key]}
        if not participants <= accepted_entities:
            gates.append("participants_not_accepted")
        if event["time"] and event["time"]["year"] is not None:
            dating = event["time"]
            if not re.search(rf"(?<!\d){dating['year']}(?!\d)", dating["original_text"] or ""):
                gates.append("normalized_year_not_explicit")
            quotes = " ".join(evidence[eid] for eid in event["evidence_ids"])
            approximate = re.search(rf"(?i)\b(kolem|asi|přibližně|cca)\s+(?:roku\s+)?{dating['year']}\b", quotes)
            if approximate and not dating["approximate"]:
                gates.append("approximate_date_lost")
        if acceptance != "model_review":
            gates.append("manual_policy")
        event["status"] = ("rejected" if decision.decision == "rejected" else
                           "requires_review" if gates else "accepted")
        applied["events"].append({**decision.model_dump(), "status": event["status"], "gates": gates})
    return Document.model_validate(value), applied


def compact_registry() -> dict:
    registry = registry_dict()
    return {"registry_version": registry["registry_version"], "crm_version": registry["crm_version"],
            "nodes": [{key: entry[key] for key in ("name", "definition", "crm_identifier", "origin")}
                      for entry in registry["nodes"] if entry["name"] in {"Person", "PhysicalThing", "Acquisition", "TimeSpan"}],
            "relationships": [{key: entry[key] for key in ("name", "definition", "source_types", "target_types", "origin")}
                              for entry in registry["relationships"]]}


def check_inventory(inventory: dict, config: PipelineConfig) -> dict[str, str]:
    available = {item["name"]: item for item in inventory.get("models", [])}
    digests = {}
    for role, settings in config.models:
        name = settings.model
        normalized = name if ":" in name.rsplit("/", 1)[-1] else name + ":latest"
        model = available.get(name) or available.get(normalized)
        if model is None:
            raise ValueError(f"Chybí lokální model {name} pro roli {role}. Stáhni jej příkazem ollama pull {name}.")
        if model.get("remote_host") or model.get("remote_model"):
            raise ValueError("Model odkazuje na vzdálenou Ollama; pipeline povoluje pouze lokální inference.")
        digests[role] = model.get("digest", "unknown")
    return digests


def run_pipeline(manifest_path: Path, config_path: Path, output: Path | None = None,
                 backend: ModelBackend | None = None, progress=None) -> dict:
    config = load_config(config_path)
    manifest = InputManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    created_at = datetime.now(timezone.utc)
    run_id = created_at.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    root = output or Path("runs") / run_id
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    started = time.monotonic()
    runner = StageRunner(backend or OllamaClient(config), config, root)
    audit = {"run_id": run_id, "status": "running", "created_at": created_at.isoformat(),
             "pipeline_version": __version__, "prompt_version": prompts.PROMPT_VERSION,
             "acceptance_policy": config.acceptance + ":" + POLICY_VERSION,
             "python": platform.python_version(), "platform": platform.platform(),
             "api_cost_usd": 0, "hardware_cost_measured": False}

    def save_audit() -> None:
        audit.update(calls=runner.calls, wall_seconds=round(time.monotonic() - started, 3),
                     prompt_tokens=sum(call.get("prompt_eval_count", 0) for call in runner.calls),
                     completion_tokens=sum(call.get("eval_count", 0) for call in runner.calls))
        (root / "run.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def report(message: str) -> None:
        if progress:
            progress(message)

    save_audit()
    try:
        report(f"Audit běhu: {root}")
        write_json(root / "config.json", config.model_dump())
        write_json(root / "input.json", manifest.model_dump())
        write_json(root / "registry.json", registry_dict())
        texts = {}
        sources = []
        input_root = manifest_path.resolve().parent
        for source in manifest.documents:
            path = (input_root / source.source_file).resolve()
            if not path.is_relative_to(input_root):
                raise ValueError("Zdrojový text musí ležet uvnitř složky vstupního manifestu.")
            text = path.read_bytes().decode("utf-8")
            if len(text) > config.max_document_chars:
                raise ValueError(f"{source.id}: dokument překračuje max_document_chars; automatické chunkování zatím není implementováno.")
            texts[source.id] = text
            snapshot = "documents/" + source.id + ".txt"
            target = root / snapshot
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(text.encode("utf-8"))
            sources.append(source.model_copy(update={"source_file": snapshot}))
        audit["source_hashes"] = {key: hashlib.sha256(text.encode("utf-8")).hexdigest() for key, text in texts.items()}
        report("Ověřuji lokální Ollama a dostupné modely.")
        inventory = runner.backend.inventory()
        write_json(root / "ollama.json", inventory)
        digests = check_inventory(inventory, config)
        provenance = RunProvenance(
            run_id=run_id, extraction_method="ollama_pipeline", pipeline_version=__version__,
            prompt_version=prompts.PROMPT_VERSION, acceptance_policy=audit["acceptance_policy"],
            created_at=created_at.isoformat(), models={role: settings.model for role, settings in config.models},
            model_digests=digests,
        )
        dataset_meta = {"schema_version": SCHEMA_VERSION, "registry_version": REGISTRY_VERSION,
                        "dataset_id": manifest.dataset_id, "dataset_version": manifest.dataset_version + "-" + run_id,
                        "provenance": provenance.model_dump()}
        extracted_documents = []
        reviewed_documents = []
        reviews = {}
        for source in sources:
            text = texts[source.id]
            report(f"{source.id}: extrakce entit.")
            context = {"document_id": source.id, "text": text, "registry": compact_registry()}
            entities = runner.call("entities", source.id, prompts.ENTITIES, context, EntityExtraction,
                                   lambda result: entity_document(source, result, text),
                                   response_schema=evidence_schema(EntityExtraction, text))
            doc = entity_document(source, entities, text)
            report(f"{source.id}: extrakce událostí.")
            context["entities"] = [entity.model_dump() for entity in doc.entities]
            context["evidence"] = [quote.model_dump() for quote in doc.evidence]
            events = runner.call("events", source.id, prompts.EVENTS, context, EventExtraction,
                                 lambda result: event_document(doc, result, text),
                                 response_schema=evidence_schema(EventExtraction, text))
            doc = event_document(doc, events, text)
            offsets = verify_evidence(doc, text)
            for quote in doc.evidence:
                quote.start, quote.end = offsets[source.id, quote.local_id]
            extracted_documents.append(doc)
            write_json(root / "documents" / (source.id + ".extracted.json"), doc.model_dump())
            report(f"{source.id}: nezávislá revize tvrzení.")
            review = runner.call("review", source.id, prompts.REVIEW,
                                 review_context(doc, text),
                                 DocumentReview, lambda result: check_review(result, doc), response_schema=review_schema(doc))
            reviewed, applied = apply_review(doc, review, config.acceptance)
            reviewed_documents.append(reviewed)
            reviews[source.id] = {"model_decisions": review.model_dump(), "applied": applied}
            save_audit()
        identity_context = {"documents": [{"document_id": doc.id, "text": texts[doc.id],
                                           "entities": [e.model_dump() for e in doc.entities],
                                           "evidence": [e.model_dump() for e in doc.evidence]}
                                          for doc in reviewed_documents]}
        proposals = []
        if len(sources) < 2:
            audit["identity_status"] = "skipped_single_document"
        elif len(json.dumps(identity_context, ensure_ascii=False)) > config.max_identity_context_chars:
            audit["identity_status"] = "deferred_context_limit"
        else:
            report("Navrhuji identity mezi dokumenty; návrhy zůstanou k revizi.")

            def identity_links(result: IdentityResolution) -> list[IdentityLink]:
                links = []
                for proposal in result.proposals:
                    if proposal.left.document_id == proposal.right.document_id:
                        raise ValueError("Návrh identity musí propojovat různé dokumenty.")
                    if not {proposal.left.document_id, proposal.right.document_id} <= {ref.document_id for ref in proposal.evidence}:
                        raise ValueError("Návrh identity potřebuje důkazy z obou dokumentů.")
                    links.append(IdentityLink.model_validate({**proposal.model_dump(), "status": "requires_review"}))
                Dataset.model_validate({**dataset_meta, "documents": reviewed_documents, "identity_links": links})
                return links

            identities = runner.call("identity", "collection", prompts.IDENTITY, identity_context,
                                     IdentityResolution, identity_links)
            proposals = identity_links(identities)
            audit["identity_status"] = "proposed_requires_review"
        candidates = Dataset.model_validate({**dataset_meta, "documents": extracted_documents, "identity_links": proposals})
        dataset = Dataset.model_validate({**dataset_meta, "documents": reviewed_documents, "identity_links": proposals})
        loaded = validate_dataset(dataset, texts)
        plan = build_plan(loaded)
        write_json(root / "candidates.json", candidates.model_dump())
        write_json(root / "reviews.json", reviews)
        write_json(root / "dataset.json", dataset.model_dump())
        write_json(root / "graph-plan.json", plan.as_dict())
        summary = {"run_id": run_id, "output": str(root), "dataset": str(root / "dataset.json"),
                   "import_id": plan.import_id, "documents": len(sources),
                   "accepted_entities": sum(e.status == "accepted" for d in dataset.documents for e in d.entities),
                   "accepted_events": sum(e.status == "accepted" for d in dataset.documents for e in d.events),
                   "events_requiring_review": sum(e.status == "requires_review" for d in dataset.documents for e in d.events),
                   "rejected_events": sum(e.status == "rejected" for d in dataset.documents for e in d.events),
                   "identity_proposals": len(proposals), "planned_nodes": len(plan.nodes), "planned_edges": len(plan.edges)}
        audit.update(status="complete", summary=summary, fingerprint=loaded.fingerprint)
        save_audit()
        return summary
    except Exception as exc:
        audit.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        save_audit()
        raise
