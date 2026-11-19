"""Deterministický plán a parametrizovaný transakční import do Neo4j."""

from dataclasses import asdict, dataclass
from typing import Any
from uuid import NAMESPACE_URL, uuid5
import hashlib
import json

from neo4j import Driver, ManagedTransaction

from kg_pipeline.ingestion import LoadedDataset
from kg_pipeline.ontology import NODE_TYPES, RELATION_TYPES


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class Edge:
    source: str
    type: str
    target: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class GraphPlan:
    import_id: str
    fingerprint: str
    nodes: list[Node]
    edges: list[Edge]

    def as_dict(self) -> dict:
        return asdict(self)


def stable_id(*parts: str) -> str:
    return str(uuid5(NAMESPACE_URL, json.dumps(parts, ensure_ascii=False)))


def build_plan(loaded: LoadedDataset) -> GraphPlan:
    dataset = loaded.dataset
    namespace = (dataset.dataset_id, dataset.dataset_version)
    import_id = stable_id(*namespace, "import")
    nodes: dict[str, Node] = {}
    edges: dict[tuple[str, str, str], Edge] = {}

    def node(node_id: str, type_label: str, **properties: Any) -> str:
        definition = NODE_TYPES[type_label]
        metadata = {"import_id": import_id, "type_uri": definition.uri,
                    "registry_version": dataset.registry_version}
        if definition.crm_identifier:
            metadata.update(crm_identifier=definition.crm_identifier, crm_version=definition.crm_version)
        nodes[node_id] = Node(node_id, type_label, metadata | properties)
        return node_id

    def edge(source: str, relationship: str, target: str, **properties: Any) -> None:
        definition = RELATION_TYPES[relationship]
        if nodes[source].label not in definition.source_types or nodes[target].label not in definition.target_types:
            raise ValueError(f"Nepovolená doména/obor hodnot: {relationship}.")
        if relationship == "SAME_ENTITY_AS" and nodes[source].label != nodes[target].label:
            raise ValueError("Totožnost smí spojovat jen stejné typy.")
        edges[(source, relationship, target)] = Edge(source, relationship, target,
                                                   {"type_uri": definition.uri} | properties)

    def local(doc_id: str, kind: str, local_id: str) -> str:
        return stable_id(*namespace, doc_id, kind, local_id)

    def support(doc_id: str, node_id: str, evidence_ids: list[str]) -> None:
        for eid in evidence_ids:
            edge(node_id, "SUPPORTED_BY", local(doc_id, "evidence", eid))

    node(import_id, "KGImport", fingerprint=loaded.fingerprint,
         dataset_id=dataset.dataset_id, dataset_version=dataset.dataset_version,
         schema_version=dataset.schema_version, pipeline_version="0.1.0", extraction_method="manual_reference")
    if dataset.provenance:
        metadata = dataset.provenance
        props = nodes[import_id].properties | {
            "pipeline_version": metadata.pipeline_version, "extraction_method": metadata.extraction_method,
            "run_id": metadata.run_id, "prompt_version": metadata.prompt_version,
            "acceptance_policy": metadata.acceptance_policy, "audit_manifest": metadata.audit_manifest,
            "models_json": json.dumps(metadata.models, sort_keys=True),
            "model_digests_json": json.dumps(metadata.model_digests, sort_keys=True),
        }
        nodes[import_id] = Node(import_id, "KGImport", props)
    # Uložení důkazů samo o sobě nezakládá tvrzení z kandidátní vrstvy.
    for doc in dataset.documents:
        text = loaded.texts[doc.id]
        document_id = node(local(doc.id, "document", doc.id), "Document", local_id=doc.id,
                           text=text, source_file=doc.source_file, synthetic=doc.synthetic,
                           sha256=hashlib.sha256(text.encode("utf-8")).hexdigest())
        for evidence in doc.evidence:
            start, end = loaded.offsets[(doc.id, evidence.local_id)]
            evidence_id = node(local(doc.id, "evidence", evidence.local_id), "Evidence",
                               text=evidence.text, start=start, end=end, document_id=doc.id)
            edge(evidence_id, "FOUND_IN", document_id)
        for entity in doc.entities:
            if entity.status != "accepted":
                continue
            entity_id = node(local(doc.id, "entity", entity.local_id), entity.type,
                             local_id=entity.local_id, document_id=doc.id, label=entity.label,
                             status="accepted", identity_status="document_local")
            support(doc.id, entity_id, entity.evidence_ids)
        for event in doc.events:
            if event.status != "accepted":
                continue
            event_id = node(local(doc.id, "event", event.local_id), "Acquisition",
                            local_id=event.local_id, document_id=doc.id, status="accepted",
                            assertion=event.assertion, epistemic_status="source_assertion")
            for entity_id, relationship in (
                (event.acquirer, "TRANSFERRED_TITLE_TO"),
                (event.former_owner, "TRANSFERRED_TITLE_FROM"),
                (event.transferred_object, "TRANSFERRED_TITLE_OF"),
            ):
                if entity_id is not None:
                    edge(event_id, relationship, local(doc.id, "entity", entity_id))
            if event.time:
                time_id = node(local(doc.id, "time", event.local_id), "TimeSpan", **event.time.model_dump())
                edge(event_id, "HAS_TIME_SPAN", time_id)
                support(doc.id, time_id, event.evidence_ids)
            support(doc.id, event_id, event.evidence_ids)
    for link in dataset.identity_links:
        if link.status != "accepted":
            continue
        left = local(link.left.document_id, "entity", link.left.entity_id)
        right = local(link.right.document_id, "entity", link.right.entity_id)
        left, right = sorted((left, right))
        edge(left, "SAME_ENTITY_AS", right, reason=link.reason, reviewed_by=link.reviewed_by,
             evidence_ids=[local(ref.document_id, "evidence", ref.evidence_id) for ref in link.evidence])
    return GraphPlan(import_id, loaded.fingerprint, sorted(nodes.values(), key=lambda n: n.id),
                     sorted(edges.values(), key=lambda e: (e.source, e.type, e.target)))


def _write_plan(tx: ManagedTransaction, plan: GraphPlan) -> dict[str, int]:
    # Identifikátory a lidská jména nikdy nevstupují do textu příkazu.
    # Zámek na markeru serializuje importy stejné verze včetně souběžných běhů.
    record = tx.run(
        "MERGE (m:KGNode:KGImport {id: $id}) "
        "ON CREATE SET m.fingerprint = $fingerprint "
        "SET m.fingerprint = m.fingerprint "
        "RETURN m.fingerprint AS fingerprint",
        id=plan.import_id, fingerprint=plan.fingerprint,
    ).single(strict=True)
    if record["fingerprint"] != plan.fingerprint:
        raise ValueError("Tato verze datasetu již obsahuje jiná data. Zvyš dataset_version; import nic nepřepsal.")
    created_nodes = 0
    created_edges = 0
    for label in NODE_TYPES:
        rows = [{"id": n.id, "properties": n.properties} for n in plan.nodes if n.label == label]
        if rows:
            result = tx.run(f"UNWIND $rows AS row MERGE (n:KGNode:{label} {{id: row.id}}) "
                            "ON CREATE SET n += row.properties "
                            "SET n.import_id = row.properties.import_id",
                            rows=rows)
            # Marker vznikl již před touto smyčkou; jeho metadata je nutné doplnit.
            created_nodes += result.consume().counters.nodes_created
    marker = next(n for n in plan.nodes if n.id == plan.import_id)
    tx.run("MATCH (n:KGNode {id: $id}) SET n += $properties",
           id=plan.import_id, properties=marker.properties).consume()
    for relationship in RELATION_TYPES:
        rows = [{"source": e.source, "target": e.target, "properties": e.properties}
                for e in plan.edges if e.type == relationship]
        if rows:
            result = tx.run(
                f"UNWIND $rows AS row MATCH (s:KGNode {{id: row.source}}), (t:KGNode {{id: row.target}}) "
                f"MERGE (s)-[r:{relationship}]->(t) ON CREATE SET r += row.properties", rows=rows,
            )
            created_edges += result.consume().counters.relationships_created
    return {"planned_nodes": len(plan.nodes), "planned_edges": len(plan.edges),
            "created_data_nodes": created_nodes, "created_edges": created_edges}


def import_plan(driver: Driver, database: str, plan: GraphPlan) -> dict[str, int]:
    with driver.session(database=database) as session:
        session.run("CREATE CONSTRAINT kg_node_id IF NOT EXISTS FOR (n:KGNode) REQUIRE n.id IS UNIQUE").consume()
        return session.execute_write(_write_plan, plan)
