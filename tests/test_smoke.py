import asyncio

from app.adapters.source.text_adapter import TextAdapter
from app.domain.reading_goal import ReadingGoal
from app.runtime.orchestrator import Orchestrator


def test_headless_smoke() -> None:
    document = TextAdapter().parse("Para 1\n\nPara 2")
    events = asyncio.run(Orchestrator().run(document, ReadingGoal(user_query="Read this paper")))
    event_types = [event.type for event in events]
    assert "document.ingested" in event_types
    assert "annotation.compiled" in event_types
    assert "run.completed" in event_types

    compiled = next(event for event in events if event.type == "annotation.compiled")
    assert "这里写批注内容" in compiled.payload["rendered_content"]
