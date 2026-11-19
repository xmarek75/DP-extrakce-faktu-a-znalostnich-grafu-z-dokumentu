"""Malý ručně schválený registr, nikoli implementace celé CIDOC CRM."""

from dataclasses import asdict, dataclass
from types import MappingProxyType

from kg_pipeline.schema import REGISTRY_VERSION

CRM_VERSION = "7.1.3"
CRM_BASE = "http://www.cidoc-crm.org/cidoc-crm/"


@dataclass(frozen=True)
class TypeDefinition:
    name: str
    definition: str
    origin: str
    uri: str
    crm_identifier: str | None = None
    crm_version: str | None = None
    source_types: tuple[str, ...] = ()
    target_types: tuple[str, ...] = ()
    official_domain: str | None = None
    official_range: str | None = None
    direction: str = "source_to_target"
    symmetric: bool = False
    inverse: str | None = None
    synonyms: tuple[str, ...] = ()
    status: str = "approved"
    schema_version: str = REGISTRY_VERSION
    approved_on: str = "2026-11-18"
    compatibility: str = "Počáteční schéma 1.0.0; bez migrace starších dat."
    source: str = "knowledge_graph_prototype_design.md; AGENTS.md"
    custom_reason: str | None = None


def crm(name: str, identifier: str, definition: str, **kwargs: object) -> TypeDefinition:
    return TypeDefinition(name, definition, "cidoc", CRM_BASE + identifier,
                          crm_identifier=identifier, crm_version=CRM_VERSION, **kwargs)


def custom(name: str, definition: str, **kwargs: object) -> TypeDefinition:
    return TypeDefinition(name, definition, "custom", "urn:dp:" + name,
                          custom_reason=definition, **kwargs)


NODE_TYPES = MappingProxyType({entry.name: entry for entry in (
    crm("Person", "E21_Person", "Zmínka osoby; identita napříč dokumenty není automaticky sjednocena."),
    crm("PhysicalThing", "E18_Physical_Thing", "Fyzická věc uvedená ve zdroji."),
    crm("Acquisition", "E8_Acquisition", "Dokumentem tvrzený převod vlastnického práva."),
    crm("TimeSpan", "E52_Time-Span", "Časové vymezení včetně původní formulace a nejistoty."),
    custom("Document", "Aplikační záznam dokumentu s původním textem a kontrolním součtem."),
    custom("Evidence", "Doslovná pasáž dokumentu s ověřenými textovými offsety."),
    custom("KGImport", "Technická metadata neměnného importu a kontrolní součet vstupu."),
)})

RELATION_TYPES = MappingProxyType({entry.name: entry for entry in (
    crm("TRANSFERRED_TITLE_TO", "P22_transferred_title_to", "Událost → nabyvatel práva.",
        source_types=("Acquisition",), target_types=("Person",),
        official_domain="E8_Acquisition", official_range="E39_Actor",
        inverse="P22i_acquired_title_through"),
    crm("TRANSFERRED_TITLE_FROM", "P23_transferred_title_from", "Událost → převodce práva.",
        source_types=("Acquisition",), target_types=("Person",),
        official_domain="E8_Acquisition", official_range="E39_Actor",
        inverse="P23i_surrendered_title_through"),
    crm("TRANSFERRED_TITLE_OF", "P24_transferred_title_of", "Událost → převáděná fyzická věc.",
        source_types=("Acquisition",), target_types=("PhysicalThing",),
        official_domain="E8_Acquisition", official_range="E18_Physical_Thing",
        inverse="P24i_changed_ownership_through"),
    crm("HAS_TIME_SPAN", "P4_has_time-span", "Událost → časové vymezení.",
        source_types=("Acquisition",), target_types=("TimeSpan",),
        official_domain="E2_Temporal_Entity", official_range="E52_Time-Span",
        inverse="P4i_is_time-span_of"),
    custom("SUPPORTED_BY", "Doložená informace → doslovný textový důkaz.",
           source_types=("Person", "PhysicalThing", "Acquisition", "TimeSpan"), target_types=("Evidence",)),
    custom("FOUND_IN", "Textový důkaz → zdrojový dokument.",
           source_types=("Evidence",), target_types=("Document",)),
    custom("SAME_ENTITY_AS", "Ručně přijatá totožnost dvou lokálních entit; neslučuje jejich záznamy.",
           source_types=("Person", "PhysicalThing"), target_types=("Person", "PhysicalThing"),
           symmetric=True),
)})


def registry_dict() -> dict:
    return {"registry_version": REGISTRY_VERSION, "crm_version": CRM_VERSION,
            "nodes": [asdict(entry) for entry in NODE_TYPES.values()],
            "relationships": [asdict(entry) for entry in RELATION_TYPES.values()]}
