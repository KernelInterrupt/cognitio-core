from __future__ import annotations

from app.adapters.llm.base import ModelProvider
from app.adapters.llm.heuristic_provider import HeuristicProvider
from app.adapters.llm.models import GuidedStepRequest, PlanRequest
from app.domain.document_ir import DocumentIR, ParagraphNode
from app.domain.reading_goal import ReadingGoal, UserIntervention
from app.prompts.loader import load_prompt
from app.protocol.events import (
    AdviceGeneratedPayload,
    AnnotationCompiledPayload,
    AnnotationCompileFailedPayload,
    AnnotationOpenedPayload,
    DocumentIngestedPayload,
    Event,
    ReadingModeInferredPayload,
    ReadingPlanCreatedPayload,
    ReadingProgressPayload,
    ResearchCompletedPayload,
    ResearchRequestedPayload,
    RunAwaitingUserInputPayload,
    RunCompletedPayload,
    RunStartedPayload,
    build_event,
)
from app.runtime.permissions import PermissionProfile
from app.runtime.session import ReadingSession
from app.runtime.tool_registry import ToolRegistry
from app.services.annotation_service import AnnotationService
from app.services.research_service import ResearchService


class Orchestrator:
    def __init__(self, provider: ModelProvider | None = None) -> None:
        self.provider = provider or HeuristicProvider()
        self.tools = ToolRegistry()
        self.annotation_service = AnnotationService(self.provider)
        self.research_service = ResearchService(self.provider)

    async def run(
        self,
        document: DocumentIR,
        goal: ReadingGoal,
        interventions: list[UserIntervention] | None = None,
        permission_tier: str = "annotate",
    ) -> list[Event]:
        session = ReadingSession(run_id="run_001", document_id=document.document_id, goal=goal)
        session.enqueue_interventions(interventions or [])
        permissions = PermissionProfile.for_tier(permission_tier)
        self.tools.bind_document(document)

        events: list[Event] = [
            build_event(
                "document.ingested",
                DocumentIngestedPayload(
                    document_id=document.document_id,
                    node_count=len(document.reading_order),
                    page_count=document.metadata.page_count,
                    localized_evidence_count=document.metadata.localized_evidence_count,
                    relation_count=document.metadata.relation_count,
                ),
            )
        ]

        plan = await self.provider.plan_reading(
            PlanRequest(
                document_ir=document,
                goal=goal,
                system_prompt=load_prompt("planning_system.md"),
            )
        )
        session.reading_mode = plan.reading_mode
        events.append(
            build_event(
                "reading_mode.inferred",
                ReadingModeInferredPayload(
                    value=plan.reading_mode,
                    source="inferred",
                ),
            )
        )
        events.append(
            build_event(
                "reading_plan.created",
                ReadingPlanCreatedPayload(
                    key_nodes=plan.key_nodes,
                    notes=plan.notes,
                    skip_hints=plan.skip_hints,
                ),
            )
        )
        events.append(
            build_event(
                "run.started",
                RunStartedPayload(
                    run_id=session.run_id,
                    provider=self.provider.name,
                    permission_tier=permissions.tier,
                ),
            )
        )

        for index, node_id in enumerate(document.reading_order, start=1):
            node = document.nodes[node_id]
            if not isinstance(node, ParagraphNode):
                continue
            node_handle = self.tools.select(node_id)

            events.append(
                build_event(
                    "reading.progress",
                    ReadingProgressPayload(
                        run_id=session.run_id,
                        node_id=node_id,
                        stage="reading",
                    ),
                )
            )
            current_interventions = session.consume_for_node(node_id)
            if current_interventions:
                events.append(
                    build_event(
                        "run.awaiting_user_input",
                        RunAwaitingUserInputPayload(
                            run_id=session.run_id,
                            node_id=node_id,
                            interventions=[
                                item.model_dump(mode="json") for item in current_interventions
                            ],
                        ),
                    )
                )

            step = await self.provider.guided_step(
                GuidedStepRequest(
                    document_id=document.document_id,
                    node_id=node_id,
                    current_node_text=node.text,
                    system_prompt=load_prompt("reading_system.md"),
                    local_context_before=[
                        document.nodes[prev_id].text
                        for prev_id in document.reading_order[max(0, index - 3) : index - 1]
                        if isinstance(document.nodes[prev_id], ParagraphNode)
                    ],
                    local_context_after=[
                        document.nodes[next_id].text
                        for next_id in document.reading_order[index : index + 2]
                        if isinstance(document.nodes[next_id], ParagraphNode)
                    ],
                    reading_mode=session.reading_mode or "mixed",
                    goal=goal,
                    plan_summary="; ".join(plan.notes),
                    key_nodes=plan.key_nodes,
                    user_interventions=current_interventions,
                )
            )

            for action in step.actions:
                if action.type == "highlight" and permissions.allows("highlight"):
                    highlight = node_handle.highlight(action.level, action.reason)
                    events.append(build_event("highlight.applied", highlight))
                elif action.type == "warning" and permissions.allows("warning"):
                    warning = node_handle.warning(
                        kind=action.kind,
                        severity=action.severity,
                        message=action.message,
                        evidence=action.evidence,
                    )
                    events.append(build_event("warning.raised", warning))
                elif action.type == "open_annotation" and permissions.allows("open_annotation"):
                    annotation = node_handle.open_annotation(
                        action.annotation_type,
                        action.language,
                    )
                    events.append(
                        build_event(
                            "annotation.opened",
                            AnnotationOpenedPayload(**annotation.model_dump(mode="json")),
                        )
                    )
                    workspace_handle, compile_result = (
                        await self.annotation_service.render_annotation(annotation)
                    )
                    if compile_result.ok:
                        events.append(
                            build_event(
                                "annotation.compiled",
                                AnnotationCompiledPayload(
                                    annotation_id=annotation.annotation_id,
                                    rendered_content=compile_result.rendered_content or "",
                                    workspace_id=workspace_handle.workspace_id,
                                ),
                            )
                        )
                    else:
                        events.append(
                            build_event(
                                "annotation.compile_failed",
                                AnnotationCompileFailedPayload(
                                    annotation_id=annotation.annotation_id,
                                    errors=[
                                        error.model_dump(mode="json")
                                        for error in compile_result.errors
                                    ],
                                ),
                        )
                    )
                elif action.type == "advice" and permissions.allows("advice"):
                    advice = node_handle.advice(action.kind, action.message, scope="node")
                    events.append(
                        build_event(
                            "advice.generated",
                            AdviceGeneratedPayload(**advice.model_dump(mode="json")),
                        )
                    )
                elif action.type == "research" and permissions.allows("research"):
                    research_request = node_handle.research(action.goal, action.scope)
                    events.append(
                        build_event(
                            "research.requested",
                            ResearchRequestedPayload(
                                task_id=research_request.task_id,
                                node_id=research_request.node_id,
                                goal=research_request.goal,
                                scope=research_request.scope,
                            ),
                        )
                    )
                    task, result = await self.research_service.run_subtask(
                        research_request,
                        node_text=node.text,
                        reading_mode=session.reading_mode or "mixed",
                    )
                    events.append(
                        build_event(
                            "research.completed",
                            ResearchCompletedPayload(
                                task_id=task.task_id,
                                node_id=task.node_id,
                                goal=task.goal,
                                findings=[
                                    finding.model_dump(mode="json")
                                    for finding in result.findings
                                ],
                                notes=result.notes,
                            ),
                        )
                    )

            if index == len(document.reading_order):
                break

        advice = self.tools.advice(
            document.document_id,
            "read_selectively",
            "Focus on highlighted nodes first.",
        )
        events.append(
            build_event(
                "advice.generated",
                AdviceGeneratedPayload(**advice.model_dump(mode="json")),
            )
        )
        events.append(build_event("run.completed", RunCompletedPayload(run_id=session.run_id)))
        return events
