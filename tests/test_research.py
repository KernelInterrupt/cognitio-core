import asyncio

from app.adapters.llm.heuristic_provider import HeuristicProvider
from app.adapters.source.text_adapter import TextAdapter
from app.domain.reading_goal import ReadingGoal
from app.domain.research import ResearchRequest
from app.runtime.orchestrator import Orchestrator
from app.runtime.permissions import PermissionProfile
from app.services.research_service import ResearchService


def test_permission_profile_allows_research_tier() -> None:
    profile = PermissionProfile.for_tier("research")
    assert profile.allows("research")


def test_research_service_returns_findings() -> None:
    service = ResearchService(HeuristicProvider())
    task, result = asyncio.run(
        service.run_subtask(
            ResearchRequest(
                task_id="research_p_1",
                node_id="p_1",
                goal="迁移到医疗场景",
                scope="node",
            ),
            node_text="This method assumes stable sensors and requires calibration.",
            reading_mode="paper_like",
        )
    )
    assert task.status == "completed"
    assert result.findings


def test_orchestrator_emits_research_events_when_enabled() -> None:
    document = TextAdapter().parse("This method assumes stable sensors.\n\nPara 2")
    orchestrator = Orchestrator()

    original_guided_step = orchestrator.provider.guided_step

    async def guided_step_with_research(request):
        response = await original_guided_step(request)
        if request.node_id == "p_1":
            from app.adapters.llm.models import ResearchAction

            response.actions.insert(1, ResearchAction(goal="迁移风险分析", scope="node"))
        return response

    orchestrator.provider.guided_step = guided_step_with_research  # type: ignore[method-assign]

    events = asyncio.run(
        orchestrator.run(
            document,
            ReadingGoal(user_query="Read this paper and think about transfer."),
            permission_tier="research",
        )
    )

    event_types = [event.type for event in events]
    assert "research.requested" in event_types
    assert "research.completed" in event_types
