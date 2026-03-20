from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from app.domain.reading_goal import ReadingGoal, UserIntervention


@dataclass
class ReadingSession:
    run_id: str
    document_id: str
    goal: ReadingGoal
    reading_mode: str | None = None
    pending_interventions: deque[UserIntervention] = field(default_factory=deque)

    def enqueue_interventions(self, interventions: list[UserIntervention]) -> None:
        self.pending_interventions.extend(interventions)

    def consume_for_node(self, node_id: str) -> list[UserIntervention]:
        matched: list[UserIntervention] = []
        remaining: deque[UserIntervention] = deque()
        while self.pending_interventions:
            item = self.pending_interventions.popleft()
            if item.at_node is None or item.at_node == node_id:
                matched.append(item)
            else:
                remaining.append(item)
        self.pending_interventions = remaining
        return matched

