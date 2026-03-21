from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.adapters.llm.base import ModelProviderError
from app.adapters.llm.models import GuidedStepRequest, GuidedStepResponse, HighlightAction
from app.adapters.llm.ollama_adapter import OllamaProvider
from app.domain.reading_goal import ReadingGoal


def test_ollama_provider_guided_step_parses_structured_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "qwen3:4b"
        assert payload["stream"] is False
        assert payload["messages"][0]["role"] == "system"
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": GuidedStepResponse(
                        actions=[HighlightAction(level="important", reason="key paragraph")],
                        notes=["ok"],
                    ).model_dump_json()
                }
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://ollama.local")
    provider = OllamaProvider(client=client)

    response = asyncio.run(provider.guided_step(
        GuidedStepRequest(
            document_id="doc_1",
            node_id="para_0001",
            current_node_text="Transformers use self-attention.",
            reading_mode="paper_like",
            goal=ReadingGoal(user_query="读这篇论文"),
        )
    ))

    assert response.actions[0].type == "highlight"
    assert response.actions[0].level == "important"


def test_ollama_provider_raises_on_invalid_json() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "not-json"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama.local")
    provider = OllamaProvider(client=client)

    with pytest.raises(ModelProviderError):
        asyncio.run(provider.guided_step(
            GuidedStepRequest(
                document_id="doc_1",
                node_id="para_0001",
                current_node_text="Transformers use self-attention.",
                reading_mode="paper_like",
                goal=ReadingGoal(user_query="读这篇论文"),
            )
        ))
