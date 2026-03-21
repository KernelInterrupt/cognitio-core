from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.domain.annotation import Annotation
from app.domain.research import ResearchRequest
from app.domain.signals import Advice, HighlightState, WarningSignal

if TYPE_CHECKING:
    from app.runtime.tool_registry import ToolRegistry


@dataclass
class NodeHandle:
    node_id: str
    tools: ToolRegistry

    def highlight(self, level: str, reason: str | None = None) -> HighlightState:
        return self.tools.highlight(self.node_id, level, reason)

    def warning(
        self,
        kind: str,
        severity: str,
        message: str,
        evidence: list[str] | None = None,
    ) -> WarningSignal:
        return self.tools.warning(self.node_id, kind, severity, message, evidence)

    def advice(self, kind: str, message: str, scope: str = "node") -> Advice:
        return self.tools.advice(self.node_id, kind, message, scope=scope)

    def open_annotation(
        self,
        annotation_type: str,
        language: str = "zh",
    ) -> Annotation:
        return self.tools.open_annotation(self.node_id, annotation_type, language)

    def research(self, goal: str, scope: str | None = None) -> ResearchRequest:
        return self.tools.research(self.node_id, goal, scope)
