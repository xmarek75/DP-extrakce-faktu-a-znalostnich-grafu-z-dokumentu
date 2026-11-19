"""Volání jedné role: schéma, omezené opravy, úplný audit a měření."""

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from kg_pipeline.extraction.config import PipelineConfig
from kg_pipeline.extraction.ollama import ModelBackend, OllamaError, generation_schema

T = TypeVar("T", bound=BaseModel)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


class StageFailure(ValueError):
    pass


class StageRunner:
    def __init__(self, backend: ModelBackend, config: PipelineConfig, root: Path):
        self.backend = backend
        self.config = config
        self.root = root
        self.calls: list[dict] = []

    def call(self, stage: str, scope: str, prompt: str, context: dict,
             response_model: type[T], check: Callable[[T], object] | None = None,
             response_schema: dict | None = None) -> T:
        settings = getattr(self.config.models, stage)
        schema = generation_schema(response_schema if response_schema is not None else response_model.model_json_schema())
        messages = [
            {"role": "system", "content": prompt + "\nJSON Schema:\n" + json.dumps(schema, ensure_ascii=False)},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ]
        for attempt in range(1, self.config.max_attempts + 1):
            prefix = self.root / "stages" / scope / stage / f"attempt-{attempt}"
            payload = {"model": settings.model, "stream": False, "format": schema,
                       "messages": messages.copy(), "keep_alive": "5m",
                       "options": settings.model_dump(exclude={"model", "think"})}
            if settings.think is not None:
                payload["think"] = settings.think
            write_json(prefix.with_suffix(".request.json"), payload)
            started = time.monotonic()
            record = {"stage": stage, "scope": scope, "model": settings.model, "attempt": attempt}
            self.calls.append(record)
            content = None
            try:
                response = self.backend.chat(payload)
                write_json(prefix.with_suffix(".response.json"), response)
                record.update({key: response[key] for key in (
                    "model", "prompt_eval_count", "eval_count", "total_duration", "load_duration"
                ) if key in response})
                content = response.get("message", {}).get("content", "")
                if response.get("error") or response.get("done") is not True:
                    raise ValueError("Ollama generování nedokončila.")
                if response.get("done_reason") == "length":
                    raise ValueError("Výstup dosáhl limitu num_predict. Zkrať dokument nebo zvyš limit.")
                value = response_model.model_validate_json(content)
                if check:
                    check(value)
                record.update(status="valid", wall_seconds=round(time.monotonic() - started, 3))
                write_json(prefix.with_suffix(".validation.json"), record)
                return value
            except (ValueError, OllamaError) as exc:
                if isinstance(exc, ValidationError):
                    details = [{"path": list(e["loc"]), "message": e["msg"]}
                               for e in exc.errors(include_input=False, include_url=False)]
                else:
                    details = str(exc)
                record.update(status="invalid", errors=details,
                              wall_seconds=round(time.monotonic() - started, 3))
                if isinstance(exc, OllamaError) and exc.response is not None:
                    record["transport_response"] = exc.response
                write_json(prefix.with_suffix(".validation.json"), record)
                if isinstance(exc, OllamaError):
                    # Síťový výpadek model nemůže opravit změnou extrahovaných dat.
                    continue
                if isinstance(content, str) and content:
                    messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": "Předchozí pokus neprošel kontrolou. "
                                 "Vrať kompletní opravený JSON podle původního zadání. Chyby: "
                                 + json.dumps(details, ensure_ascii=False)})
        if isinstance(details, list):
            last_error = "; ".join(".".join(map(str, error["path"])) + ": " + error["message"]
                                   for error in details[:3])
        else:
            last_error = details
        raise StageFailure(f"Krok {stage} pro {scope} neprošel po {self.config.max_attempts} pokusech. "
                           f"Poslední kontrola: {last_error[:600]}. Viz audit v {self.root}.")
