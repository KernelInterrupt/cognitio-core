from __future__ import annotations

import os
from typing import Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"


class OllamaEndpointStatus(BaseModel):
    base_url: str
    reachable: bool = False
    status: Literal["ok", "http_error", "network_error"]
    num_models: int | None = None
    message: str | None = None
    models: list[str] = Field(default_factory=list)


def resolve_ollama_base_url(base_url: str | None = None) -> str:
    return (base_url or os.getenv("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def build_ollama_connectivity_hint(base_url: str) -> str:
    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 11434
    return (
        "Ollama is unreachable from the current backend environment. "
        f"Tried {base_url}. Verify that Ollama is running and that this environment can reach "
        f"{host}:{port}. If the model service is not reachable at the default address, set "
        "OLLAMA_BASE_URL explicitly instead of relying on machine-specific assumptions."
    )


async def probe_ollama_endpoint(
    base_url: str | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> OllamaEndpointStatus:
    resolved = resolve_ollama_base_url(base_url)
    owns_client = client is None
    http_client = client or httpx.AsyncClient(base_url=resolved, timeout=5.0)
    try:
        response = await http_client.get("/api/tags")
        if response.status_code >= 400:
            return OllamaEndpointStatus(
                base_url=resolved,
                reachable=False,
                status="http_error",
                message=f"Unexpected status {response.status_code}: {response.text}",
            )
        payload = response.json()
        models = [item.get("name", "") for item in payload.get("models", []) if item.get("name")]
        return OllamaEndpointStatus(
            base_url=resolved,
            reachable=True,
            status="ok",
            num_models=len(models),
            models=models,
            message="Ollama API reachable.",
        )
    except httpx.HTTPError as exc:
        return OllamaEndpointStatus(
            base_url=resolved,
            reachable=False,
            status="network_error",
            message=f"{exc.__class__.__name__}: {exc}",
        )
    finally:
        if owns_client:
            await http_client.aclose()
