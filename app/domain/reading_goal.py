from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReadingGoal(BaseModel):
    user_query: str
    constraints: list[str] = Field(default_factory=list)
    target_domain: str | None = None


class UserIntervention(BaseModel):
    intervention_id: str
    run_id: str
    kind: Literal[
        "clarify_goal",
        "change_priority",
        "ask_question",
        "request_skip",
        "focus_node",
        "request_pause",
    ]
    message: str
    at_node: str | None = None

