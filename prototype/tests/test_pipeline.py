"""Testy orchestrace s náhradou modelu; aplikace referenční JSON nečte."""

import json

import pytest
from pydantic import ValidationError

from kg_pipeline.extraction.config import load_config
from kg_pipeline.extraction.ollama import OllamaClient, OllamaError, generation_schema
from kg_pipeline.extraction.pipeline import apply_review, check_inventory, evidence_schema, review_context, review_schema, run_pipeline
from kg_pipeline.extraction.models import DocumentReview, EntityExtraction, EventExtraction, ExtractedTimeSpan
from kg_pipeline.extraction.runner import StageFailure
from kg_pipeline.graph import build_plan
from kg_pipeline.ingestion import load_dataset
from kg_pipeline.schema import Document


@pytest.fixture
def pipeline_config(tmp_path):
    path = tmp_path / "pipeline.toml"
    path.write_text('max_attempts = 2\n' + "\n".join(
        f'[models.{role}]\nmodel = "{role}-model:local"\n'
        for role in ("entities", "events", "review", "identity")
    ), encoding="utf-8")
    return path


class FakeBackend:
    def __init__(self, reference, mutate=None):
        self.docs = {doc["id"]: doc for doc in reference["documents"]}
        self.links = reference["identity_links"]
        self.requests = []
        self.mutate = mutate

    def inventory(self):
        return {"server": {"version": "test-double"}, "models": [
            {"name": role + "-model:local", "digest": "test-digest-" + role}
            for role in ("entities", "events", "review", "identity")
        ]}

    def chat(self, payload):
        self.requests.append(payload)
        role = payload["model"].split("-model:")[0]
        context = json.loads(payload["messages"][1]["content"])
        if role == "identity":
            content = {"proposals": [{key: value for key, value in link.items()
                                      if key not in {"status", "reviewed_by"}} for link in self.links]}
        else:
            doc_id = context.get("document_id") or context["extraction"]["id"]
            doc = self.docs[doc_id]
            if role == "entities":
                content = {"entities": [{key: value for key, value in entity.items() if key != "status"}
                                        for entity in doc["entities"]], "evidence": doc["evidence"]}
            elif role == "events":
                content = {"events": [{key: value for key, value in event.items() if key != "status"}
                                      for event in doc["events"]], "evidence": [], "candidates": doc.get("candidates", [])}
            else:
                content = {"entities": [{"local_id": entity["local_id"], "decision": "supported", "reason": "Doloženo citací."}
                                        for entity in doc["entities"]],
                           "events": [{"local_id": event["local_id"], "decision": "supported", "reason": "Role a čas odpovídají.",
                                       "roles_supported": True, "time_supported": True, "modality_preserved": True}
                                      for event in doc["events"]]}
        # Oddělíme objekty od referenčních fixtures, aby mutace neovlivnily další fázi.
        content = json.loads(json.dumps(content))
        if self.mutate:
            content = self.mutate(role, content, len(self.requests))
        return {"model": payload["model"], "done": True, "done_reason": "stop",
                "message": {"content": json.dumps(content, ensure_ascii=False)},
                "prompt_eval_count": 17, "eval_count": 31}


def test_complete_pipeline_uses_four_configured_models_and_original_texts(dataset_path, raw_dataset, pipeline_config, tmp_path):
    backend = FakeBackend(raw_dataset)
    output = tmp_path / "run"
    result = run_pipeline(dataset_path.parent / "input.json", pipeline_config, output, backend)
    assert result["accepted_events"] == 3
    assert result["accepted_entities"] == 9
    assert result["identity_proposals"] == 2
    assert {request["model"] for request in backend.requests} == {
        "entities-model:local", "events-model:local", "review-model:local", "identity-model:local"}
    assert len(backend.requests) == 10
    assert all(request["stream"] is False and isinstance(request["format"], dict) for request in backend.requests)
    candidates = json.loads((output / "candidates.json").read_text())
    assert all(event["status"] == "requires_review" for doc in candidates["documents"] for event in doc["events"])
    loaded = load_dataset(output / "dataset.json")
    assert all(link.status == "requires_review" and link.reviewed_by is None for link in loaded.dataset.identity_links)
    assert loaded.dataset.documents[2].events[0].time.approximate is True
    assert len(loaded.dataset.documents[2].candidates) == 2
    plan = build_plan(loaded)
    assert not any(edge.type in {"SAME_ENTITY_AS", "FRIEND_OF"} for edge in plan.edges)
    marker = next(node for node in plan.nodes if node.label == "KGImport")
    assert marker.properties["extraction_method"] == "ollama_pipeline"
    for doc in loaded.dataset.documents:
        assert loaded.texts[doc.id] == (dataset_path.parent / "documents" / (doc.id + ".txt")).read_text()
    audit = json.loads((output / "run.json").read_text())
    assert audit["status"] == "complete"
    assert audit["prompt_tokens"] == 170 and audit["completion_tokens"] == 310
    assert len(list(output.glob("stages/**/*.response.json"))) == 10
    assert loaded.dataset.provenance.model_digests["review"] == "test-digest-review"


def test_invalid_quote_is_retried_and_audited(dataset_path, raw_dataset, pipeline_config, tmp_path):
    def mutate(role, data, call):
        if role == "entities":
            data["evidence"][0]["text"] = "Tato věta ve vstupu neexistuje."
        return data
    output = tmp_path / "failed"
    with pytest.raises(StageFailure, match="entities"):
        run_pipeline(dataset_path.parent / "input.json", pipeline_config, output, FakeBackend(raw_dataset, mutate))
    audit = json.loads((output / "run.json").read_text())
    assert audit["status"] == "failed"
    assert len(audit["calls"]) == 2
    assert len(list(output.glob("stages/**/*.response.json"))) == 2
    assert not (output / "dataset.json").exists()


@pytest.mark.parametrize("response_model", [EntityExtraction, EventExtraction])
def test_evidence_generation_uses_exact_source_lines(dataset_path, response_model):
    text = (dataset_path.parent / "documents/doc_003.txt").read_text(encoding="utf-8")
    schema = evidence_schema(response_model, text)
    allowed = schema["$defs"]["Quote"]["properties"]["text"]["enum"]
    assert "Kolem roku 1530 koupil Matěj Kovář z Olomouce zahradu od Jana Dlouhého." in allowed
    # Regrese skutečné chybné odpovědi: změněné první písmeno a ztracená datace.
    assert "Koupil Matěj Kovář z Olomouce zahradu od Jana Dlouhého." not in allowed
    assert "koupil Matěj Kovář z Olomouce zahradu od Jana Dlouhého." not in allowed
    assert "Koupě mlýna se neuskutečnila." in allowed
    assert all(quote in text for quote in allowed)


def test_evidence_catalog_preserves_characters_and_handles_empty_input():
    text = "  Kolem roku 1530 koupil Matěj zahradu.\r\nÚdajně byl přítelem Jana.\r\n"
    allowed = evidence_schema(EntityExtraction, text)["$defs"]["Quote"]["properties"]["text"]["enum"]
    assert allowed == ["Kolem roku 1530 koupil Matěj zahradu.", "Údajně byl přítelem Jana."]
    assert all(quote in text for quote in allowed)
    assert evidence_schema(EntityExtraction, " \r\n\t")["properties"]["evidence"]["maxItems"] == 0


@pytest.mark.parametrize("stage", ["entities", "events"])
def test_shortened_but_literal_quote_is_not_accepted(dataset_path, raw_dataset, pipeline_config, tmp_path, stage):
    def mutate(role, data, call):
        if role == stage:
            body = "koupil Matěj Kovář od Václava Svobody dům U Modré hvězdy v Brně."
            if stage == "entities":
                data["evidence"][0]["text"] = body
            else:
                data["evidence"] = [{"local_id": "partial", "text": body}]
        return data

    with pytest.raises(StageFailure, match="celý povolený zdrojový úsek"):
        run_pipeline(dataset_path.parent / "input.json", pipeline_config, tmp_path / "run", FakeBackend(raw_dataset, mutate))


def test_quote_repair_keeps_approximate_source_wording(dataset_path, raw_dataset, pipeline_config, tmp_path):
    class QuoteRepairBackend(FakeBackend):
        changed = False
        quote_options = None

        def chat(self, payload):
            context = json.loads(payload["messages"][1]["content"])
            if payload["model"] == "entities-model:local" and context["document_id"] == "doc_003":
                self.quote_options = payload["format"]["$defs"]["Quote"]["properties"]["text"]["enum"]
                response = super().chat(payload)
                if not self.changed:
                    self.changed = True
                    data = json.loads(response["message"]["content"])
                    data["evidence"][0]["text"] = "Koupil Matěj Kovář z Olomouce zahradu od Jana Dlouhého."
                    response["message"]["content"] = json.dumps(data, ensure_ascii=False)
                return response
            return super().chat(payload)

    backend = QuoteRepairBackend(raw_dataset)
    output = tmp_path / "run"
    result = run_pipeline(dataset_path.parent / "input.json", pipeline_config, output, backend)
    assert result["accepted_events"] == 3
    loaded = load_dataset(output / "dataset.json")
    doc = loaded.dataset.documents[2]
    assert doc.evidence[0].text.startswith("Kolem roku 1530")
    assert doc.events[0].time.approximate is True
    assert doc.evidence[0].text in backend.quote_options
    attempts = [call for call in json.loads((output / "run.json").read_text())["calls"]
                if call["scope"] == "doc_003" and call["stage"] == "entities"]
    assert [call["status"] for call in attempts] == ["invalid", "valid"]


@pytest.mark.parametrize("failure", ["self_acceptance", "wrong_entity_reference", "changed_quote", "incomplete_review"])
def test_model_cannot_bypass_validation(dataset_path, raw_dataset, pipeline_config, tmp_path, failure):
    def mutate(role, data, call):
        if failure == "self_acceptance" and role == "entities":
            data["entities"][0]["status"] = "accepted"
        if failure == "wrong_entity_reference" and role == "events":
            data["events"][0]["acquirer"] = "invented-person"
        if failure == "changed_quote" and role == "events":
            data["evidence"] = [{"local_id": "ev1", "text": "Pozměněná citace."}]
        if failure == "incomplete_review" and role == "review":
            data["entities"] = []
        return data
    with pytest.raises(StageFailure):
        run_pipeline(dataset_path.parent / "input.json", pipeline_config, tmp_path / "run", FakeBackend(raw_dataset, mutate))


def test_repair_can_succeed_and_keeps_both_attempts(dataset_path, raw_dataset, pipeline_config, tmp_path):
    def mutate(role, data, call):
        if call == 1:
            data["entities"][0]["evidence_ids"] = ["missing"]
        return data
    backend = FakeBackend(raw_dataset, mutate)
    output = tmp_path / "repaired"
    result = run_pipeline(dataset_path.parent / "input.json", pipeline_config, output, backend)
    assert result["accepted_events"] == 3 and len(backend.requests) == 11
    audit = json.loads((output / "run.json").read_text())
    assert [call["status"] for call in audit["calls"][:2]] == ["invalid", "valid"]


def test_missing_original_time_is_repaired_with_previous_response(dataset_path, raw_dataset, pipeline_config, tmp_path):
    def mutate(role, data, call):
        if role == "events" and call == 2:
            # Regrese skutečné odpovědi qwen2.5:3b: rok bez doslovné formulace.
            del data["events"][0]["time"]["original_text"]
        return data

    backend = FakeBackend(raw_dataset, mutate)
    result = run_pipeline(dataset_path.parent / "input.json", pipeline_config, tmp_path / "run", backend)
    assert result["accepted_events"] == 3
    first_request, retry = backend.requests[1:3]
    time_schema = first_request["format"]["$defs"]["ExtractedTimeSpan"]
    assert set(time_schema["required"]) == {"original_text", "year", "precision", "approximate"}
    assert [message["role"] for message in retry["messages"]] == ["system", "user", "assistant", "user"]
    previous = json.loads(retry["messages"][-2]["content"])
    assert "original_text" not in previous["events"][0]["time"]
    assert "original_text" in retry["messages"][-1]["content"]
    validation = json.loads((tmp_path / "run/stages/doc_001/events/attempt-1.validation.json").read_text())
    assert validation["errors"][0]["path"] == ["events", 0, "time", "original_text"]


def test_incomplete_year_rejected_at_the_missing_field(raw_dataset):
    event = {key: value for key, value in raw_dataset["documents"][0]["events"][0].items() if key != "status"}
    event["time"] = {"precision": "year", "year": 1521, "approximate": False}
    with pytest.raises(ValidationError) as exc:
        EventExtraction.model_validate({"events": [event], "evidence": [], "candidates": []})
    assert exc.value.errors()[0]["loc"] == ("events", 0, "time", "original_text")


def test_transport_failure_retries_the_same_prompt(dataset_path, raw_dataset, pipeline_config, tmp_path):
    class FlakyBackend(FakeBackend):
        failed_request = None
        retry_request = None

        def chat(self, payload):
            if payload["model"] == "review-model:local":
                if self.failed_request is None:
                    self.failed_request = payload
                    raise OllamaError("Vypršel časový limit.")
                if self.retry_request is None:
                    self.retry_request = payload
            return super().chat(payload)

    backend = FlakyBackend(raw_dataset)
    result = run_pipeline(dataset_path.parent / "input.json", pipeline_config, tmp_path / "run", backend)
    assert result["accepted_events"] == 3
    assert backend.failed_request["messages"] == backend.retry_request["messages"]
    assert len(backend.retry_request["messages"]) == 2


def test_review_generation_contract_restricts_count_and_ids(raw_dataset):
    doc = Document.model_validate(raw_dataset["documents"][0])
    schema = review_schema(doc)
    assert schema["properties"]["entities"]["minItems"] == schema["properties"]["entities"]["maxItems"] == 3
    assert schema["properties"]["events"]["minItems"] == schema["properties"]["events"]["maxItems"] == 1
    assert schema["$defs"]["ReviewDecision"]["properties"]["local_id"]["enum"] == ["p1", "p2", "obj1"]
    assert schema["$defs"]["EventReview"]["properties"]["local_id"]["enum"] == ["e1"]
    assert schema["$defs"]["ReviewDecision"]["properties"]["reason"]["maxLength"] == 200
    doc.events = []
    assert review_schema(doc)["properties"]["events"]["maxItems"] == 0


def test_review_checks_content_without_candidate_status_priming(raw_dataset):
    doc = Document.model_validate(raw_dataset["documents"][2])
    original = "Kolem roku 1530 koupil Matěj zahradu. Údajně znal Jana. Koupě mlýna se neuskutečnila."
    context = review_context(doc, original)
    assert context["text"] == original
    assert set(context["extraction"]) == {"id", "entities", "events", "evidence"}
    assert all("status" not in item for field in ("entities", "events") for item in context["extraction"][field])
    assert context["extraction"]["events"][0]["assertion"] == doc.events[0].assertion
    assert context["extraction"]["events"][0]["time"]["approximate"] is True
    assert context["extraction"]["evidence"][0]["text"] == doc.evidence[0].text


def test_ollama_schema_keeps_length_bounds_and_pydantic_rejects_whitespace():
    original = {"type": "object", "properties": {
        "reason": {"type": "string", "pattern": r"\S", "minLength": 1, "maxLength": 200},
        "local_id": {"type": "string", "pattern": r"^[A-Za-z0-9_.-]+$"},
    }}
    adapted = generation_schema(original)
    assert "pattern" not in adapted["properties"]["reason"]
    assert adapted["properties"]["reason"]["maxLength"] == 200
    assert adapted["properties"]["reason"]["minLength"] == 1
    assert adapted["properties"]["local_id"]["pattern"] == r"^[A-Za-z0-9_.-]+$"
    assert original["properties"]["reason"]["pattern"] == r"\S"
    with pytest.raises(ValidationError):
        DocumentReview.model_validate({"entities": [{"local_id": "p1", "decision": "supported", "reason": "   "}], "events": []})


def test_uncertain_time_remains_supported_without_an_invented_year(raw_dataset):
    dating = ExtractedTimeSpan.model_validate({"original_text": "tehdy", "year": None,
                                             "precision": "unknown", "approximate": False})
    assert dating.year is None and dating.original_text == "tehdy"
    event = {key: value for key, value in raw_dataset["documents"][0]["events"][0].items() if key != "status"}
    event["time"] = None
    assert EventExtraction.model_validate({"events": [event], "evidence": [], "candidates": []}).events[0].time is None


def test_manual_policy_never_auto_accepts(dataset_path, raw_dataset, pipeline_config, tmp_path):
    pipeline_config.write_text('acceptance = "manual"\n' + pipeline_config.read_text())
    result = run_pipeline(dataset_path.parent / "input.json", pipeline_config, tmp_path / "run", FakeBackend(raw_dataset))
    assert result["accepted_entities"] == result["accepted_events"] == 0
    assert result["events_requiring_review"] == 3


def test_failed_review_checks_block_acceptance(dataset_path, raw_dataset, pipeline_config, tmp_path):
    def mutate(role, data, call):
        if role == "review":
            data["events"][0]["roles_supported"] = False
        return data
    result = run_pipeline(dataset_path.parent / "input.json", pipeline_config, tmp_path / "run", FakeBackend(raw_dataset, mutate))
    assert result["accepted_events"] == 0
    assert result["events_requiring_review"] == 3


@pytest.mark.parametrize("change", ["negated", "uncertain", "wrong_year", "lost_approximation", "same_party"])
def test_deterministic_gates_override_positive_reviewer(raw_dataset, change):
    doc = Document.model_validate(raw_dataset["documents"][2])
    event = doc.events[0]
    event.status = "requires_review"
    if change in {"negated", "uncertain"}:
        event.assertion = change
    elif change == "wrong_year":
        event.time.year = 1540
    elif change == "same_party":
        event.former_owner = event.acquirer
    else:
        event.time.approximate = False
    review = DocumentReview.model_validate({
        "entities": [{"local_id": e.local_id, "decision": "supported", "reason": "test"} for e in doc.entities],
        "events": [{"local_id": event.local_id, "decision": "supported", "reason": "test",
                    "roles_supported": True, "time_supported": True, "modality_preserved": True}],
    })
    result, applied = apply_review(doc, review, "model_review")
    assert result.events[0].status == "requires_review"
    assert applied["events"][0]["gates"]


def test_identity_limit_is_explicit_and_does_not_truncate(dataset_path, raw_dataset, pipeline_config, tmp_path):
    pipeline_config.write_text('max_identity_context_chars = 1\n' + pipeline_config.read_text())
    backend = FakeBackend(raw_dataset)
    output = tmp_path / "run"
    run_pipeline(dataset_path.parent / "input.json", pipeline_config, output, backend)
    assert len(backend.requests) == 9
    assert json.loads((output / "run.json").read_text())["identity_status"] == "deferred_context_limit"


def test_long_document_stops_before_model_calls(dataset_path, raw_dataset, pipeline_config, tmp_path):
    pipeline_config.write_text('max_document_chars = 1\n' + pipeline_config.read_text())
    backend = FakeBackend(raw_dataset)
    with pytest.raises(ValueError, match="max_document_chars"):
        run_pipeline(dataset_path.parent / "input.json", pipeline_config, tmp_path / "run", backend)
    assert not backend.requests


def test_output_directory_is_not_overwritten(dataset_path, raw_dataset, pipeline_config, tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        run_pipeline(dataset_path.parent / "input.json", pipeline_config, output, FakeBackend(raw_dataset))


@pytest.mark.parametrize("url", ["https://api.example.com", "http://192.168.1.1:11434", "http://user:secret@localhost:11434", "http://localhost:11434?redirect=1"])
def test_nonlocal_endpoints_are_rejected(pipeline_config, url):
    pipeline_config.write_text('base_url = "' + url + '"\n' + pipeline_config.read_text())
    with pytest.raises(ValidationError):
        load_config(pipeline_config)


def test_remote_model_is_not_used(pipeline_config):
    config = load_config(pipeline_config)
    inventory = {"models": [{"name": "entities-model:local", "remote_host": "https://ollama.com"}]}
    with pytest.raises(ValueError, match="vzdálenou"):
        check_inventory(inventory, config)


def test_missing_model_is_actionable(pipeline_config):
    with pytest.raises(ValueError, match="ollama pull entities-model:local"):
        check_inventory({"models": []}, load_config(pipeline_config))


def test_ollama_http_protocol(pipeline_config):
    client = OllamaClient(load_config(pipeline_config))
    requests = []

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b'{"done":true,"message":{"content":"{}"}}'

    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            assert timeout == 300
            return Response()

    client.opener = Opener()
    payload = {"model": "entities-model:local", "format": {"type": "object"}, "stream": False}
    assert client.chat(payload)["done"] is True
    assert requests[0].full_url == "http://127.0.0.1:11434/api/chat"
    assert json.loads(requests[0].data) == payload
