from __future__ import annotations

import asyncio

import httpx

from app.adapters.llm.ollama_connectivity import (
    DEFAULT_OLLAMA_BASE_URL,
    build_ollama_connectivity_hint,
    probe_ollama_endpoint,
    resolve_ollama_base_url,
)


def test_resolve_ollama_base_url_prefers_explicit_value() -> None:
    assert resolve_ollama_base_url("http://10.0.0.5:11434/") == "http://10.0.0.5:11434"


def test_resolve_ollama_base_url_defaults_to_localhost() -> None:
    assert resolve_ollama_base_url(None) == DEFAULT_OLLAMA_BASE_URL


def test_build_ollama_connectivity_hint_mentions_explicit_config() -> None:
    hint = build_ollama_connectivity_hint("http://127.0.0.1:11434")
    assert "OLLAMA_BASE_URL" in hint
    assert "machine-specific assumptions" in hint


def test_probe_ollama_endpoint_reads_model_names() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "qwen3:4b"}, {"name": "gemma3:4b"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama.local")
    result = asyncio.run(probe_ollama_endpoint("http://ollama.local", client=client))

    assert result.reachable is True
    assert result.models == ["qwen3:4b", "gemma3:4b"]


def test_probe_ollama_endpoint_reports_network_error() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama.local")
    result = asyncio.run(probe_ollama_endpoint("http://ollama.local", client=client))

    assert result.reachable is False
    assert result.status == "network_error"
