from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Command(BaseModel):
    protocol_version: str = "1.0"
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)

