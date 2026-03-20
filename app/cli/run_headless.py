from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from app.adapters.llm.registry import create_provider
from app.adapters.source.text_adapter import TextAdapter
from app.domain.reading_goal import ReadingGoal, UserIntervention
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


@app.command()
def main(
    input: Annotated[
        Path,
        typer.Option(..., exists=True, readable=True, help="Path to input text document."),
    ],
    goal: Annotated[str, typer.Option(..., help="Goal-conditioned reading instruction.")],
    provider: Annotated[
        str,
        typer.Option(help="Provider name: heuristic or openai."),
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
    raw_text = input.read_text(encoding="utf-8")
    document = TextAdapter().parse(raw_text)
    model_provider = create_provider(provider, model=model)
    queued_interventions = _load_interventions(interventions)
    events = asyncio.run(
        Orchestrator(model_provider).run(
            document,
            ReadingGoal(user_query=goal),
            interventions=queued_interventions,
            permission_tier=permission_tier,
        )
    )

    for event in events:
        if jsonl:
            console.print(json.dumps(event.model_dump(), ensure_ascii=False))
        else:
            payload = " ".join(f"{k}={v}" for k, v in event.payload.items())
            console.print(f"[{event.type}] {payload}".strip())


if __name__ == "__main__":
    app()
