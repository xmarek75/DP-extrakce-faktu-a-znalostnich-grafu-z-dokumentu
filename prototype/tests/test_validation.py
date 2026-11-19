import pytest
from pydantic import ValidationError

from conftest import save_dataset
from kg_pipeline.ingestion import load_dataset
from kg_pipeline.schema import Dataset


def test_reference_and_offsets(loaded):
    assert len(loaded.dataset.documents) == 3
    assert all(doc.synthetic for doc in loaded.dataset.documents)
    for doc in loaded.dataset.documents:
        for evidence in doc.evidence:
            start, end = loaded.offsets[doc.id, evidence.local_id]
            assert loaded.texts[doc.id][start:end] == evidence.text


@pytest.mark.parametrize("field,value", [
    ("acquirer", "missing"), ("acquirer", "obj1"),
    ("transferred_object", "p1"), ("evidence_ids", ["missing"]),
    ("evidence_ids", []), ("type", "UnapprovedEvent"),
    ("assertion", "negated"), ("assertion", "uncertain"), ("assertion", "attributed"),
])
def test_invalid_event_rejected(raw_dataset, field, value):
    raw_dataset["documents"][0]["events"][0][field] = value
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw_dataset)


@pytest.mark.parametrize("mutation", ["duplicate_entity", "duplicate_document", "unknown_entity_type",
                                       "missing_entity_evidence", "unaccepted_participant", "unknown_precision",
                                       "unknown_with_year", "year_without_value", "wrong_time_quote",
                                       "unknown_schema", "unknown_registry", "extra_field"])
def test_invalid_structure_rejected(raw_dataset, mutation):
    doc = raw_dataset["documents"][0]
    if mutation == "duplicate_entity":
        doc["entities"].append(doc["entities"][0].copy())
    elif mutation == "duplicate_document":
        raw_dataset["documents"].append(doc.copy())
    elif mutation == "unknown_entity_type":
        doc["entities"][0]["type"] = "UnapprovedPerson"
    elif mutation == "missing_entity_evidence":
        del doc["entities"][0]["evidence_ids"]
    elif mutation == "unaccepted_participant":
        doc["entities"][0]["status"] = "requires_review"
    elif mutation == "unknown_precision":
        doc["events"][0]["time"]["precision"] = "day"
    elif mutation == "unknown_with_year":
        doc["events"][0]["time"]["precision"] = "unknown"
    elif mutation == "year_without_value":
        doc["events"][0]["time"]["year"] = None
    elif mutation == "wrong_time_quote":
        doc["events"][0]["time"]["original_text"] = "Roku 1900"
    elif mutation == "unknown_schema":
        raw_dataset["schema_version"] = "2.0.0"
    elif mutation == "unknown_registry":
        raw_dataset["registry_version"] = "2.0.0"
    elif mutation == "extra_field":
        doc["events"][0]["execute_cypher"] = "RETURN 1"
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw_dataset)


@pytest.mark.parametrize("mutation", ["missing_entity", "missing_evidence", "missing_reviewer",
                                       "wrong_type", "self_link", "missing_source_document"])
def test_invalid_identity_rejected(raw_dataset, mutation):
    link = raw_dataset["identity_links"][0]
    if mutation == "missing_entity":
        link["left"]["entity_id"] = "missing"
    elif mutation == "missing_evidence":
        link["evidence"][0]["evidence_id"] = "missing"
    elif mutation == "missing_reviewer":
        link["reviewed_by"] = None
    elif mutation == "wrong_type":
        link["right"]["entity_id"] = "obj1"
    elif mutation == "self_link":
        link["right"] = link["left"].copy()
    elif mutation == "missing_source_document":
        link["evidence"] = link["evidence"][1:]
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw_dataset)


def test_quote_must_exist(dataset_path, raw_dataset):
    raw_dataset["documents"][0]["evidence"][0]["text"] += " Vymyšlený dodatek."
    save_dataset(dataset_path, raw_dataset)
    with pytest.raises(ValueError, match="nenachází"):
        load_dataset(dataset_path)


@pytest.mark.parametrize("start,end", [(0, 10), (5, None), (None, 10), (-1, 10), (10, 5), (58, 10000)])
def test_bad_offsets_rejected(dataset_path, raw_dataset, start, end):
    raw_dataset["documents"][0]["evidence"][0].update(start=start, end=end)
    save_dataset(dataset_path, raw_dataset)
    with pytest.raises(ValueError):
        load_dataset(dataset_path)


def test_repeated_quote_requires_offsets(dataset_path, raw_dataset):
    source = dataset_path.parent / raw_dataset["documents"][0]["source_file"]
    source.write_text(source.read_text(encoding="utf-8") * 2, encoding="utf-8")
    with pytest.raises(ValueError, match="opakovaný"):
        load_dataset(dataset_path)
    quote = raw_dataset["documents"][0]["evidence"][0]
    start = source.read_text(encoding="utf-8").rfind(quote["text"])
    quote.update(start=start, end=start + len(quote["text"]))
    save_dataset(dataset_path, raw_dataset)
    assert load_dataset(dataset_path).offsets["doc_001", "ev1"][0] == start


def test_end_offset_cannot_exceed_source(dataset_path, raw_dataset):
    quote = raw_dataset["documents"][0]["evidence"][0]
    source = dataset_path.parent / raw_dataset["documents"][0]["source_file"]
    # I kdyby citát končil na konci souboru, Python slice mimo rozsah nesmí projít.
    source.write_text(quote["text"], encoding="utf-8")
    quote.update(start=0, end=10000)
    save_dataset(dataset_path, raw_dataset)
    with pytest.raises(ValueError, match="offsety"):
        load_dataset(dataset_path)


def test_duplicate_identity_pair_rejected(raw_dataset):
    duplicate = raw_dataset["identity_links"][0].copy()
    duplicate["local_id"] = "other_id"
    duplicate["left"], duplicate["right"] = duplicate["right"], duplicate["left"]
    raw_dataset["identity_links"].append(duplicate)
    with pytest.raises(ValidationError, match="Duplicitní propojení"):
        Dataset.model_validate(raw_dataset)


def test_source_cannot_escape_dataset(dataset_path, raw_dataset):
    raw_dataset["documents"][0]["source_file"] = "../../outside.txt"
    save_dataset(dataset_path, raw_dataset)
    with pytest.raises(ValueError, match="uvnitř"):
        load_dataset(dataset_path)


def test_original_crlf_offsets_preserved(dataset_path):
    source = dataset_path.parent / "documents" / "doc_001.txt"
    source.write_bytes(source.read_bytes().replace(b"\n", b"\r\n"))
    loaded = load_dataset(dataset_path)
    assert "\r\n" in loaded.texts["doc_001"]
    assert loaded.offsets["doc_001", "ev1"][0] == loaded.texts["doc_001"].index("Roku 1521")
