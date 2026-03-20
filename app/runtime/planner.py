from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.document_ir import DocumentIR, ParagraphNode
from app.domain.reading_goal import ReadingGoal


class ReadingPlan(BaseModel):
    reading_mode: str
    key_nodes: list[str] = Field(default_factory=list)
    skip_hints: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Planner:
    """Simple heuristic planner for the first MVP."""

    def create_plan(self, document: DocumentIR, goal: ReadingGoal) -> ReadingPlan:
        goal_text = goal.user_query.lower()
        reading_mode = "instructional" if any(
            token in goal_text for token in ("install", "manual", "hardware", "step")
        ) else "paper_like"

        key_nodes: list[str] = []
        for node_id in document.reading_order[: min(3, len(document.reading_order))]:
            node = document.nodes[node_id]
            if isinstance(node, ParagraphNode):
                key_nodes.append(node_id)

        notes = [f"Goal-aware mode selected: {reading_mode}"]
        return ReadingPlan(reading_mode=reading_mode, key_nodes=key_nodes, notes=notes)

