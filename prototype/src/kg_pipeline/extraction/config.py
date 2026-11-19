"""Konfigurace lokálních modelů bez závislosti na konkrétním orchestrátoru."""

import tomllib
from pathlib import Path
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from kg_pipeline.schema import StrictModel, Text


class ModelConfig(StrictModel):
    model: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$")]
    temperature: Annotated[float, Field(ge=0, le=2)] = 0.0
    seed: int = 42
    num_ctx: Annotated[int, Field(ge=4096, le=131072)] = 16384
    num_predict: Annotated[int, Field(ge=128, le=16384)] = 4096
    think: bool | None = None

    @model_validator(mode="after")
    def local_model(self) -> Self:
        if "cloud" in self.model.lower():
            raise ValueError("Tato pipeline povoluje pouze lokální Ollama modely.")
        return self


class StageModels(StrictModel):
    entities: ModelConfig
    events: ModelConfig
    review: ModelConfig
    identity: ModelConfig


class PipelineConfig(StrictModel):
    base_url: Text = "http://127.0.0.1:11434"
    timeout_seconds: Annotated[int, Field(ge=1, le=3600)] = 300
    max_attempts: Annotated[int, Field(ge=1, le=3)] = 2
    max_document_chars: Annotated[int, Field(ge=1)] = 8000
    max_identity_context_chars: Annotated[int, Field(ge=1)] = 18000
    acceptance: Literal["model_review", "manual"] = "model_review"
    models: StageModels

    @model_validator(mode="after")
    def local_endpoint(self) -> Self:
        parsed = urlsplit(self.base_url)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
            raise ValueError("Ollama endpoint musí být lokální HTTP adresa bez přihlašovacích údajů.")
        return self


def load_config(path: Path) -> PipelineConfig:
    return PipelineConfig.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
