from conftest import save_dataset
from kg_pipeline.graph import build_plan
from kg_pipeline.ingestion import load_dataset
from kg_pipeline.ontology import NODE_TYPES, RELATION_TYPES


def test_plan_deterministic_and_local_ids_are_scoped(loaded, plan):
    assert build_plan(loaded) == plan
    persons = [n for n in plan.nodes if n.label == "Person"]
    assert len(persons) == 6
    assert len({n.id for n in persons if n.properties["local_id"] == "p1"}) == 3
    assert len([n for n in plan.nodes if n.label == "Acquisition"]) == 3
    assert len([e for e in plan.edges if e.type == "SAME_ENTITY_AS"]) == 2
    olomouc = next(n for n in persons if n.properties["document_id"] == "doc_003" and n.properties["local_id"] == "p1")
    assert not any(e.type == "SAME_ENTITY_AS" and olomouc.id in (e.source, e.target) for e in plan.edges)


def test_every_edge_has_approved_semantics(plan):
    nodes = {n.id: n for n in plan.nodes}
    for edge in plan.edges:
        definition = RELATION_TYPES[edge.type]
        assert definition.status == "approved"
        assert nodes[edge.source].label in definition.source_types
        assert nodes[edge.target].label in definition.target_types
    assert RELATION_TYPES["TRANSFERRED_TITLE_TO"].crm_identifier == "P22_transferred_title_to"
    assert RELATION_TYPES["TRANSFERRED_TITLE_FROM"].crm_identifier == "P23_transferred_title_from"
    assert NODE_TYPES["Person"].crm_version == "7.1.3"
    for name in ("SUPPORTED_BY", "FOUND_IN", "SAME_ENTITY_AS"):
        assert RELATION_TYPES[name].origin == "custom"
        assert RELATION_TYPES[name].crm_identifier is None


def test_proposals_do_not_modify_registry_or_graph(plan, loaded):
    assert loaded.dataset.documents[2].candidates[0].proposed_type == "FRIEND_OF"
    assert "FRIEND_OF" not in RELATION_TYPES
    assert not any(e.type == "FRIEND_OF" for e in plan.edges)
    assert len([n for n in plan.nodes if n.label == "Acquisition"]) == 3


def test_approximate_year_is_preserved(plan):
    time = next(n for n in plan.nodes if n.label == "TimeSpan" and n.properties["year"] == 1530)
    assert time.properties["approximate"] is True
    assert time.properties["precision"] == "year"
    assert time.properties["original_text"] == "Kolem roku 1530"
    assert not {"day", "month", "date"} & time.properties.keys()


def test_unknown_time_does_not_invent_year(dataset_path, raw_dataset):
    raw_dataset["documents"][2]["events"][0]["time"] = {"precision": "unknown"}
    save_dataset(dataset_path, raw_dataset)
    plan = build_plan(load_dataset(dataset_path))
    times = [n for n in plan.nodes if n.label == "TimeSpan"]
    assert len(times) == 3
    assert any(n.properties["precision"] == "unknown" and n.properties["year"] is None for n in times)


def test_unaccepted_event_and_identity_stay_out(dataset_path, raw_dataset):
    raw_dataset["documents"][2]["events"][0].update(status="requires_review", assertion="uncertain")
    raw_dataset["identity_links"][0]["status"] = "requires_review"
    save_dataset(dataset_path, raw_dataset)
    plan = build_plan(load_dataset(dataset_path))
    assert len([n for n in plan.nodes if n.label == "Acquisition"]) == 2
    assert len([e for e in plan.edges if e.type == "SAME_ENTITY_AS"]) == 1


def test_changed_input_changes_fingerprint_but_version_defines_namespace(dataset_path, raw_dataset, loaded, plan):
    raw_dataset["documents"][0]["entities"][0]["label"] = "Jiná normalizace"
    save_dataset(dataset_path, raw_dataset)
    changed = load_dataset(dataset_path)
    assert changed.fingerprint != loaded.fingerprint
    assert build_plan(changed).import_id == plan.import_id
    raw_dataset["dataset_version"] = "1.0.1"
    save_dataset(dataset_path, raw_dataset)
    assert build_plan(load_dataset(dataset_path)).import_id != plan.import_id
