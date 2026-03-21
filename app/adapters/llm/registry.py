from __future__ import annotations

from app.adapters.llm.base import ModelProvider
from app.adapters.llm.heuristic_provider import HeuristicProvider
from app.adapters.llm.ollama_adapter import OllamaProvider
from app.adapters.llm.openai_adapter import OpenAIProvider


def create_provider(name: str, **kwargs: object) -> ModelProvider:
    normalized = name.lower()
    if normalized == "heuristic":
        return HeuristicProvider()
    if normalized == "openai":
        return OpenAIProvider(**kwargs)
    if normalized == "ollama":
        return OllamaProvider(**kwargs)
    raise ValueError(f"Unknown provider: {name}")

