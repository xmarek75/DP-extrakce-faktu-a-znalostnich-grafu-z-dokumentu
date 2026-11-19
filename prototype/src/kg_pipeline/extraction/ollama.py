"""Malý klient oficiálního Ollama HTTP API se strukturovaným výstupem."""

import json
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from kg_pipeline.extraction.config import PipelineConfig


class OllamaError(RuntimeError):
    def __init__(self, message: str, response: str | None = None):
        super().__init__(message)
        self.response = response


class ModelBackend(Protocol):
    def inventory(self) -> dict: ...
    def chat(self, payload: dict) -> dict: ...


def generation_schema(schema: dict) -> dict:
    """Zachová limity délky i při nepodporovaném pomocném regexu Text."""
    def adapt(value):
        if isinstance(value, dict):
            # Ollama pro neukotvené \S hlásí fallback na libovolný řetězec,
            # který obchází i maxLength. Neprázdnost dál kontroluje Pydantic.
            return {key: adapt(item) for key, item in value.items()
                    if not (key == "pattern" and item == r"\S")}
        if isinstance(value, list):
            return [adapt(item) for item in value]
        return value
    return adapt(schema)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OllamaClient:
    def __init__(self, config: PipelineConfig):
        self.config = config
        # Lokální dokumenty nesmějí odejít přes proxy ani HTTP přesměrování.
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def _request(self, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = Request(self.config.base_url.rstrip("/") + path, data=body,
                          headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=self.config.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
                if not isinstance(data, dict):
                    raise OllamaError("Ollama vrátila neplatný formát odpovědi.")
                return data
        except HTTPError as exc:
            response = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama HTTP {exc.code}; podrobnosti jsou v auditu běhu.", response) from None
        except (URLError, TimeoutError, ConnectionError):
            raise OllamaError("Lokální Ollama není dostupná nebo vypršel časový limit. Ověř server a timeout_seconds.") from None
        except (json.JSONDecodeError, UnicodeError):
            raise OllamaError("Ollama nevrátila platnou JSON odpověď.") from None

    def inventory(self) -> dict:
        return {"server": self._request("/api/version"), "models": self._request("/api/tags").get("models", [])}

    def chat(self, payload: dict) -> dict:
        return self._request("/api/chat", payload)
