from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.domain.reading_goal import ReadingGoal


class ReadingRun(BaseModel):
    run_id: str
    document_id: str
    status: Literal["idle", "planning", "running", "paused", "completed", "failed"] = "idle"
    reading_mode: str | None = None
    goal: ReadingGoal
    cursor_node_id: str | None = None

