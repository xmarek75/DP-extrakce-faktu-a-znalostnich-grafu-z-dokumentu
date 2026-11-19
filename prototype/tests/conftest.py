import json
import shutil
from pathlib import Path

import pytest

from kg_pipeline.graph import build_plan
from kg_pipeline.ingestion import load_dataset

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def dataset_path(tmp_path):
    shutil.copytree(EXAMPLES, tmp_path / "examples")
    return tmp_path / "examples" / "reference.json"


@pytest.fixture
def raw_dataset(dataset_path):
    return json.loads(dataset_path.read_text(encoding="utf-8"))


@pytest.fixture
def loaded(dataset_path):
    return load_dataset(dataset_path)


@pytest.fixture
def plan(loaded):
    return build_plan(loaded)


def save_dataset(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
