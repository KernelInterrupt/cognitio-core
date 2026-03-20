from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

HighlightLevel = Literal["skip", "normal", "important", "critical"]


class HighlightState(BaseModel):
    node_id: str
    level: HighlightLevel
    reason: str | None = None


class WarningSignal(BaseModel):
    warning_id: str
    target_node_id: str
    kind: Literal[
        "prompt_injection",
        "hidden_text",
        "instruction_like_content",
        "unsupported_claim",
        "weak_evidence",
        "overclaim",
        "evaluation_risk",
    ]
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    evidence: list[str] = Field(default_factory=list)


class Advice(BaseModel):
    advice_id: str
    scope: Literal["node", "section", "document", "run"]
    target_id: str
    kind: Literal[
        "continue_reading",
        "read_selectively",
        "skip_section",
        "revisit_node",
        "stop_reading",
        "validate_externally",
    ]
    message: str
    basis: list[str] = Field(default_factory=list)
