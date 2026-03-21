from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from app.adapters.llm.base import ModelProviderError
from app.adapters.llm.ollama_connectivity import (
    build_ollama_connectivity_hint,
    probe_ollama_endpoint,
    resolve_ollama_base_url,
)
from app.adapters.llm.registry import create_provider
from app.domain.reading_goal import ReadingGoal, UserIntervention
from app.ingest.factory import build_default_router
from app.ingest.source import DocumentSource
from app.runtime.orchestrator import Orchestrator

app = typer.Typer(help="Run the headless guided-reading MVP.")
console = Console()


def _load_interventions(path: Path | None) -> list[UserIntervention]:
    if path is None:
        return []

    items: list[UserIntervention] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        payload.setdefault("intervention_id", f"int_{index}")
        payload.setdefault("run_id", "run_001")
        items.append(UserIntervention(**payload))
    return items


def _emit_cli_event(event_type: str, payload: dict[str, object], *, jsonl: bool) -> None:
    if jsonl:
        console.print(json.dumps({"type": event_type, "payload": payload}, ensure_ascii=False))
        return
    rendered = " ".join(f"{k}={v}" for k, v in payload.items())
    console.print(f"[{event_type}] {rendered}".strip())


async def _preflight_provider(provider: str, model: str, *, jsonl: bool) -> None:
    if provider.lower() != "ollama":
        return

    base_url = resolve_ollama_base_url()
    status = await probe_ollama_endpoint(base_url)
    _emit_cli_event(
        "provider.probe",
        {
            "provider": "ollama",
            "base_url": status.base_url,
            "status": status.status,
            "reachable": status.reachable,
            "num_models": status.num_models,
        },
        jsonl=jsonl,
    )
    if not status.reachable:
        raise ModelProviderError(
            build_ollama_connectivity_hint(status.base_url)
            + (f" Probe detail: {status.message}" if status.message else "")
        )

    if model not in status.models:
        available = ", ".join(status.models[:8]) or "<none>"
        raise ModelProviderError(
            f"Ollama is reachable at {status.base_url}, but model '{model}' is not available. "
            f"Available models: {available}. Pull it first with `ollama pull {model}` or choose "
            "an installed model."
        )


async def _run_main(
    input: Path,
    goal: str,
    provider: str,
    model: str,
    interventions: Path | None,
    permission_tier: str,
    jsonl: bool,
) -> None:
    await _preflight_provider(provider, model, jsonl=jsonl)
    reading_goal = ReadingGoal(user_query=goal)
    document = await build_default_router().aingest_to_ir(
        DocumentSource.from_path(input),
        goal=reading_goal,
    )
    model_provider = create_provider(provider, model=model)
    queued_interventions = _load_interventions(interventions)
    events = await Orchestrator(model_provider).run(
        document,
        reading_goal,
        interventions=queued_interventions,
        permission_tier=permission_tier,
    )

    for event in events:
        _emit_cli_event(event.type, event.payload, jsonl=jsonl)


async def _probe_ollama_main(model: str, jsonl: bool) -> None:
    await _preflight_provider("ollama", model, jsonl=jsonl)


@app.command()
def main(
    input: Annotated[
        Path,
        typer.Option(..., exists=True, readable=True, help="Path to input document."),
    ],
    goal: Annotated[str, typer.Option(..., help="Goal-conditioned reading instruction.")],
    provider: Annotated[
        str,
        typer.Option(help="Provider name: heuristic, openai, or ollama."),
    ] = "heuristic",
    model: Annotated[
        str,
        typer.Option(
            help="Model name used by provider implementations that need one.",
        ),
    ] = "gpt-5-mini",
    interventions: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            readable=True,
            help="Optional JSONL file with queued interventions.",
        ),
    ] = None,
    permission_tier: Annotated[
        str,
        typer.Option(
            help="Permission tier: observe, annotate, research, sandboxed_exec.",
        ),
    ] = "annotate",
    jsonl: Annotated[
        bool,
        typer.Option(help="Emit JSONL instead of human-readable events."),
    ] = False,
) -> None:
    asyncio.run(
        _run_main(
            input=input,
            goal=goal,
            provider=provider,
            model=model,
            interventions=interventions,
            permission_tier=permission_tier,
            jsonl=jsonl,
        )
    )


@app.command("probe-ollama")
def probe_ollama(
    model: Annotated[
        str,
        typer.Option(
            help="Model name that should already be available in the target Ollama service.",
        ),
    ] = "qwen3:4b",
    jsonl: Annotated[
        bool,
        typer.Option(help="Emit JSONL instead of human-readable events."),
    ] = False,
) -> None:
    asyncio.run(_probe_ollama_main(model=model, jsonl=jsonl))


if __name__ == "__main__":
    app()
