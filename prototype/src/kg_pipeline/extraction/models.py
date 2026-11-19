"""Kontrakty jednotlivých modelových kroků; LLM nemůže přijímat vlastní výstup."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from kg_pipeline.schema import (
    Candidate, EntityRef, EvidenceIds, EvidenceRef, Identifier, StrictModel,
    Text, TimeSpan, require_unique,
)


class InputDocument(StrictModel):
    id: Identifier
    source_file: Text
    synthetic: bool = False


class InputManifest(StrictModel):
    dataset_id: Identifier
    dataset_version: Identifier
    documents: Annotated[list[InputDocument], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_documents(self) -> Self:
        require_unique([doc.id for doc in self.documents], "vstupní dokumenty")
        return self


class Quote(StrictModel):
    local_id: Identifier
    text: Text


class ExtractedEntity(StrictModel):
    local_id: Identifier
    type: Literal["Person", "PhysicalThing"]
    label: Text
    evidence_ids: EvidenceIds


class EntityExtraction(StrictModel):
    entities: list[ExtractedEntity]
    evidence: list[Quote]


class ExtractedTimeSpan(TimeSpan):
    """Generovací kontrakt: model musí vyplnit čas i jeho doslovný podklad."""

    original_text: Text = Field(description="Doslovná formulace datace z důkazu, například Roku 1521.")
    year: Annotated[int, Field(ge=1, le=9999)] | None
    approximate: bool


class ExtractedAcquisition(StrictModel):
    local_id: Identifier
    type: Literal["Acquisition"]
    assertion: Literal["affirmed", "negated", "uncertain", "attributed"]
    acquirer: Identifier | None
    former_owner: Identifier | None
    transferred_object: Identifier
    time: ExtractedTimeSpan | None
    evidence_ids: EvidenceIds


class EventExtraction(StrictModel):
    events: list[ExtractedAcquisition]
    evidence: list[Quote]
    candidates: list[Candidate]


class ReviewDecision(StrictModel):
    local_id: Identifier
    decision: Literal["supported", "requires_review", "rejected"]
    reason: Annotated[Text, Field(max_length=200)]


class EventReview(ReviewDecision):
    roles_supported: bool
    time_supported: bool
    modality_preserved: bool


class DocumentReview(StrictModel):
    entities: list[ReviewDecision]
    events: list[EventReview]


class IdentityProposal(StrictModel):
    local_id: Identifier
    left: EntityRef
    right: EntityRef
    reason: Text
    evidence: Annotated[list[EvidenceRef], Field(min_length=1)]


class IdentityResolution(StrictModel):
    proposals: list[IdentityProposal]
