"""Načtení originálních textů a ověření důkazů v jejich původních souřadnicích."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from kg_pipeline.schema import Dataset, Document


@dataclass(frozen=True)
class LoadedDataset:
    dataset: Dataset
    texts: dict[str, str]
    offsets: dict[tuple[str, str], tuple[int, int]]
    fingerprint: str


def load_dataset(path: Path) -> LoadedDataset:
    dataset = Dataset.model_validate_json(path.read_text(encoding="utf-8"))
    root = path.resolve().parent
    texts: dict[str, str] = {}
    for doc in dataset.documents:
        source = (root / doc.source_file).resolve()
        if not source.is_relative_to(root):
            raise ValueError(f"{doc.id}: zdroj musí ležet uvnitř složky datasetu.")
        # Zachováme i CRLF; offsety jsou indexy Unicode znaků, nikoli bajtů.
        text = source.read_bytes().decode("utf-8")
        texts[doc.id] = text
    return validate_dataset(dataset, texts)


def verify_evidence(doc: Document, text: str) -> dict[tuple[str, str], tuple[int, int]]:
    offsets = {}
    for evidence in doc.evidence:
        start, end = evidence.start, evidence.end
        if start is None:
            start = text.find(evidence.text)
            if start < 0:
                raise ValueError(f"{doc.id}/{evidence.local_id}: důkaz se v textu nenachází.")
            if text.find(evidence.text, start + 1) >= 0:
                raise ValueError(f"{doc.id}/{evidence.local_id}: opakovaný důkaz potřebuje ověřitelné offsety.")
            end = start + len(evidence.text)
        if end > len(text) or text[start:end] != evidence.text:
            raise ValueError(f"{doc.id}/{evidence.local_id}: offsety neodpovídají důkazu.")
        offsets[(doc.id, evidence.local_id)] = (start, end)
    return offsets


def validate_dataset(dataset: Dataset, texts: dict[str, str]) -> LoadedDataset:
    offsets = {}
    for doc in dataset.documents:
        offsets.update(verify_evidence(doc, texts[doc.id]))
    data = dataset.model_dump(exclude_none=False)
    # Zachováme původní fingerprint již importovaných referenčních dat 1.0.0.
    if dataset.schema_version == "1.0.0":
        data.pop("provenance", None)
    canonical = json.dumps({"dataset": data, "texts": texts},
                           ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return LoadedDataset(dataset, texts, offsets, fingerprint)
