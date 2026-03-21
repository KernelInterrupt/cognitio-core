from __future__ import annotations

from app.adapters.llm.base import ModelProvider
from app.adapters.llm.models import ResearchSubtaskRequest
from app.domain.research import ResearchRequest, ResearchResult, ResearchTask
from app.prompts.loader import load_prompt


class ResearchService:
    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    async def run_subtask(
        self,
        request: ResearchRequest,
        *,
        node_text: str,
        reading_mode: str,
    ) -> tuple[ResearchTask, ResearchResult]:
        task = ResearchTask(
            task_id=request.task_id,
            node_id=request.node_id,
            goal=request.goal,
            scope=request.scope,
            status="running",
        )
        response = await self.provider.research_subtask(
            ResearchSubtaskRequest(
                task_id=request.task_id,
                node_id=request.node_id,
                goal=request.goal,
                scope=request.scope,
                node_text=node_text,
                reading_mode=reading_mode,
                system_prompt=load_prompt("research_system.md"),
            )
        )
        task.status = "completed"
        result = ResearchResult(
            task_id=request.task_id,
            node_id=request.node_id,
            goal=request.goal,
            findings=response.findings,
            notes=response.notes,
        )
        return task, result
