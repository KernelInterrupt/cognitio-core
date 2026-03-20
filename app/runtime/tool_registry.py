from __future__ import annotations

from app.domain.annotation import Annotation
from app.domain.signals import Advice, HighlightState, WarningSignal
from app.runtime.node_handle import NodeHandle


class ToolRegistry:
    """Thin placeholder for future structured tool bindings."""

    def select(self, node_id: str) -> NodeHandle:
        return NodeHandle(node_id=node_id, tools=self)

    def highlight(self, node_id: str, level: str, reason: str | None = None) -> HighlightState:
        return HighlightState(node_id=node_id, level=level, reason=reason)

    def warning(
        self,
        node_id: str,
        kind: str,
        severity: str,
        message: str,
        evidence: list[str] | None = None,
    ) -> WarningSignal:
        return WarningSignal(
            warning_id=f"warn_{node_id}",
            target_node_id=node_id,
            kind=kind,
            severity=severity,
            message=message,
            evidence=evidence or [],
        )

    def advice(self, target_id: str, kind: str, message: str, scope: str = "run") -> Advice:
        return Advice(
            advice_id=f"adv_{target_id}",
            scope=scope,
            target_id=target_id,
            kind=kind,
            message=message,
        )

    def open_annotation(
        self,
        node_id: str,
        annotation_type: str,
        language: str = "zh",
    ) -> Annotation:
        return Annotation(
            annotation_id=f"ann_{node_id}",
            target_node_id=node_id,
            type=annotation_type,
            language=language,
            status="editing",
        )

    def research(self, node_id: str, goal: str, scope: str | None = None) -> dict[str, str | None]:
        return {"node_id": node_id, "goal": goal, "scope": scope}
