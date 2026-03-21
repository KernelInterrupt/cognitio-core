from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.adapters.source.text_adapter import TextAdapter
from app.cli import run_headless

runner = CliRunner()


class DummyRouter:
    async def aingest_to_ir(self, _source, *, goal):
        return TextAdapter().parse(f"Goal: {goal.user_query}\n\nParagraph 2")


class DummyOrchestrator:
    def __init__(self, _provider) -> None:
        pass

    async def run(self, document, goal, interventions, permission_tier):
        first_node_id = document.reading_order[0]
        assert document.nodes[first_node_id].text.startswith("Goal:")
        assert goal.user_query == "读这篇论文"
        assert interventions == []
        assert permission_tier == "annotate"
        return []


@pytest.mark.parametrize("provider", ["heuristic", "openai"])
def test_preflight_provider_is_noop_for_non_ollama(provider: str) -> None:
    asyncio.run(run_headless._preflight_provider(provider, "ignored", jsonl=True))


def test_preflight_provider_accepts_reachable_ollama_model(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_probe(_base_url: str):
        from app.adapters.llm.ollama_connectivity import OllamaEndpointStatus

        return OllamaEndpointStatus(
            base_url="http://127.0.0.1:11434",
            reachable=True,
            status="ok",
            num_models=2,
            models=["qwen3:4b", "gemma3:4b"],
            message="ok",
        )

    monkeypatch.setattr(run_headless, "probe_ollama_endpoint", fake_probe)
    asyncio.run(run_headless._preflight_provider("ollama", "qwen3:4b", jsonl=True))


def test_preflight_provider_rejects_unreachable_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_probe(_base_url: str):
        from app.adapters.llm.ollama_connectivity import OllamaEndpointStatus

        return OllamaEndpointStatus(
            base_url="http://127.0.0.1:11434",
            reachable=False,
            status="network_error",
            num_models=None,
            models=[],
            message="ConnectError: connection refused",
        )

    monkeypatch.setattr(run_headless, "probe_ollama_endpoint", fake_probe)

    with pytest.raises(run_headless.ModelProviderError, match="Ollama is unreachable"):
        asyncio.run(run_headless._preflight_provider("ollama", "qwen3:4b", jsonl=True))



def test_preflight_provider_rejects_missing_ollama_model(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_probe(_base_url: str):
        from app.adapters.llm.ollama_connectivity import OllamaEndpointStatus

        return OllamaEndpointStatus(
            base_url="http://127.0.0.1:11434",
            reachable=True,
            status="ok",
            num_models=1,
            models=["gemma3:4b"],
            message="ok",
        )

    monkeypatch.setattr(run_headless, "probe_ollama_endpoint", fake_probe)

    with pytest.raises(run_headless.ModelProviderError, match="ollama pull qwen3:4b"):
        asyncio.run(run_headless._preflight_provider("ollama", "qwen3:4b", jsonl=True))



def test_run_main_invokes_ollama_preflight(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, bool]] = []

    async def fake_preflight(provider: str, model: str, *, jsonl: bool) -> None:
        calls.append((provider, model, jsonl))

    monkeypatch.setattr(run_headless, "_preflight_provider", fake_preflight)
    monkeypatch.setattr(run_headless, "build_default_router", lambda: DummyRouter())
    monkeypatch.setattr(
        run_headless,
        "create_provider",
        lambda provider, model: {"provider": provider, "model": model},
    )
    monkeypatch.setattr(run_headless, "Orchestrator", DummyOrchestrator)

    input_path = tmp_path / "paper.txt"
    input_path.write_text("Paragraph 1\n\nParagraph 2", encoding="utf-8")

    asyncio.run(
        run_headless._run_main(
            input=input_path,
            goal="读这篇论文",
            provider="ollama",
            model="qwen3:4b",
            interventions=None,
            permission_tier="annotate",
            jsonl=True,
        )
    )

    assert calls == [("ollama", "qwen3:4b", True)]



def test_probe_ollama_command_emits_json(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_preflight(provider: str, model: str, *, jsonl: bool) -> None:
        run_headless._emit_cli_event(
            "provider.probe",
            {
                "provider": provider,
                "model": model,
                "reachable": True,
            },
            jsonl=jsonl,
        )

    monkeypatch.setattr(run_headless, "_preflight_provider", fake_preflight)
    result = runner.invoke(run_headless.app, ["probe-ollama", "--model", "qwen3:4b", "--jsonl"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip())
    assert payload["type"] == "provider.probe"
    assert payload["payload"]["model"] == "qwen3:4b"
