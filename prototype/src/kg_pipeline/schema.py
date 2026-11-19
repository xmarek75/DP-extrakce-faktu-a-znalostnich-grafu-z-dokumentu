"""Verzovaný meziformát; validita struktury nepotvrzuje pravdivost tvrzení."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.1.0"
REGISTRY_VERSION = "1.0.0"
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]
Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
EvidenceIds = Annotated[list[Identifier], Field(min_length=1)]
Status = Literal["accepted", "requires_review", "unsupported_type", "rejected"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Evidence(StrictModel):
    local_id: Identifier
    text: Text
    start: Annotated[int, Field(ge=0)] | None = None
    end: Annotated[int, Field(ge=1)] | None = None

    @model_validator(mode="after")
    def paired_offsets(self) -> Self:
        if (self.start is None) != (self.end is None):
            raise ValueError("Důkaz musí mít oba offsety, nebo žádný.")
        if self.start is not None and self.end <= self.start:
            raise ValueError("Konec důkazu musí následovat po začátku.")
        return self


class Entity(StrictModel):
    local_id: Identifier
    type: Literal["Person", "PhysicalThing"]
    label: Text
    status: Status = "requires_review"
    evidence_ids: EvidenceIds


class TimeSpan(StrictModel):
    original_text: Text | None = None
    year: Annotated[int, Field(ge=1, le=9999)] | None = None
    precision: Literal["year", "unknown"]
    approximate: bool = False

    @model_validator(mode="after")
    def preserve_precision(self) -> Self:
        if self.precision == "year" and (self.year is None or not self.original_text):
            raise ValueError("Roční datace potřebuje rok i původní formulaci.")
        if self.precision == "unknown" and self.year is not None:
            raise ValueError("Neznámá datace nesmí obsahovat normalizovaný rok.")
        return self


class Acquisition(StrictModel):
    local_id: Identifier
    type: Literal["Acquisition"]
    status: Status = "requires_review"
    assertion: Literal["affirmed", "negated", "uncertain", "attributed"] = "affirmed"
    acquirer: Identifier | None = None
    former_owner: Identifier | None = None
    transferred_object: Identifier
    time: TimeSpan | None = None
    evidence_ids: EvidenceIds

    @model_validator(mode="after")
    def accepted_assertion(self) -> Self:
        if self.status == "accepted" and self.assertion != "affirmed":
            raise ValueError("Negované, údajné a připsané tvrzení vyžaduje revizi.")
        if self.acquirer is None and self.former_owner is None:
            raise ValueError("Převod potřebuje alespoň jednoho doloženého účastníka.")
        return self


class Candidate(StrictModel):
    """Nepodporované informace a návrhy typů; nikdy se neimportují jako hrany."""

    local_id: Identifier
    kind: Literal["claim", "type_proposal"]
    proposed_type: Text
    status: Literal["requires_review", "unsupported_type", "rejected"]
    description: Text
    evidence_ids: EvidenceIds


def require_unique(values: list[str], context: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicitní ID: {context}.")


class Document(StrictModel):
    id: Identifier
    source_file: Text
    synthetic: bool
    entities: list[Entity]
    evidence: list[Evidence]
    events: list[Acquisition]
    candidates: list[Candidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def local_references(self) -> Self:
        for name in ("entities", "evidence", "events", "candidates"):
            require_unique([item.local_id for item in getattr(self, name)], f"{self.id}/{name}")
        entities = {item.local_id: item for item in self.entities}
        evidence = {item.local_id: item for item in self.evidence}
        for item in [*self.entities, *self.events, *self.candidates]:
            if not set(item.evidence_ids) <= evidence.keys():
                raise ValueError(f"{self.id}/{item.local_id}: neexistující důkaz.")
        for event in self.events:
            roles = [(event.acquirer, "Person"), (event.former_owner, "Person"),
                     (event.transferred_object, "PhysicalThing")]
            for entity_id, expected_type in roles:
                if entity_id is None:
                    continue
                entity = entities.get(entity_id)
                if entity is None or entity.type != expected_type:
                    raise ValueError(f"{self.id}/{event.local_id}: neplatná reference {entity_id} ({expected_type}).")
                if event.status == "accepted" and entity.status != "accepted":
                    raise ValueError("Přijatá událost smí odkazovat jen na přijaté entity.")
            if event.time and event.time.original_text:
                if not any(event.time.original_text in evidence[eid].text for eid in event.evidence_ids):
                    raise ValueError("Původní datace není součástí důkazu události.")
        return self


class EntityRef(StrictModel):
    document_id: Identifier
    entity_id: Identifier


class EvidenceRef(StrictModel):
    document_id: Identifier
    evidence_id: Identifier


class IdentityLink(StrictModel):
    local_id: Identifier
    left: EntityRef
    right: EntityRef
    status: Literal["accepted", "requires_review", "rejected"]
    reason: Text
    reviewed_by: Text | None = None
    evidence: Annotated[list[EvidenceRef], Field(min_length=1)]


class RunProvenance(StrictModel):
    run_id: Identifier
    extraction_method: Literal["ollama_pipeline"]
    pipeline_version: Text
    prompt_version: Text
    acceptance_policy: Text
    created_at: Text
    models: dict[str, str]
    model_digests: dict[str, str]
    audit_manifest: Text = "run.json"


class Dataset(StrictModel):
    schema_version: Literal["1.0.0", "1.1.0"]
    registry_version: Literal["1.0.0"]
    dataset_id: Identifier
    dataset_version: Identifier
    documents: Annotated[list[Document], Field(min_length=1)]
    identity_links: list[IdentityLink] = Field(default_factory=list)
    provenance: RunProvenance | None = None

    @model_validator(mode="after")
    def identity_references(self) -> Self:
        if self.schema_version == "1.0.0" and self.provenance is not None:
            raise ValueError("Metadata automatické extrakce vyžadují schéma 1.1.0.")
        require_unique([doc.id for doc in self.documents], "documents")
        require_unique([link.local_id for link in self.identity_links], "identity_links")
        docs = {doc.id: doc for doc in self.documents}
        pairs: set[tuple[tuple[str, str], ...]] = set()
        for link in self.identity_links:
            pair = tuple(sorted((ref.document_id, ref.entity_id) for ref in (link.left, link.right)))
            if pair in pairs:
                raise ValueError("Duplicitní propojení stejné dvojice identit; sjednoť důkazy do jednoho záznamu.")
            pairs.add(pair)
            resolved = []
            for ref in (link.left, link.right):
                doc = docs.get(ref.document_id)
                entity = next((e for e in doc.entities if e.local_id == ref.entity_id), None) if doc else None
                if entity is None:
                    raise ValueError(f"{link.local_id}: neexistující identita.")
                resolved.append(entity)
            if link.left == link.right or resolved[0].type != resolved[1].type:
                raise ValueError("Propojení identit potřebuje dvě různé entity stejného typu.")
            for ref in link.evidence:
                doc = docs.get(ref.document_id)
                if doc is None or not any(e.local_id == ref.evidence_id for e in doc.evidence):
                    raise ValueError(f"{link.local_id}: neexistující důkaz identity.")
            if link.status == "accepted":
                if not link.reviewed_by or any(e.status != "accepted" for e in resolved):
                    raise ValueError("Přijaté propojení vyžaduje revizi a přijaté entity.")
                if not {link.left.document_id, link.right.document_id} <= {r.document_id for r in link.evidence}:
                    raise ValueError("Přijaté propojení potřebuje důkazy z obou dokumentů.")
        return self
