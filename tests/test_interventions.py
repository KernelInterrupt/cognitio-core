import asyncio

from app.adapters.source.text_adapter import TextAdapter
from app.domain.reading_goal import ReadingGoal, UserIntervention
from app.runtime.orchestrator import Orchestrator


def test_intervention_creates_checkpoint_event() -> None:
    document = TextAdapter().parse("Para 1\n\nPara 2")
    intervention = UserIntervention(
        intervention_id="int_1",
        run_id="run_001",
        kind="change_priority",
        message="Focus on practical constraints.",
        at_node="p_1",
    )

    events = asyncio.run(
        Orchestrator().run(
            document,
            ReadingGoal(user_query="Read this paper"),
            interventions=[intervention],
        )
    )

    awaiting = [event for event in events if event.type == "run.awaiting_user_input"]
    assert awaiting
    assert awaiting[0].payload["node_id"] == "p_1"

    opened_for_first = [
        event
        for event in events
        if event.type == "annotation.opened" and event.payload["target_node_id"] == "p_1"
    ]
    assert not opened_for_first
