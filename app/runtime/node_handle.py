from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.domain.annotation import Annotation
from app.domain.document_ir import DocumentRelation, IRNode
from app.domain.research import ResearchRequest
from app.domain.signals import Advice, HighlightState, WarningSignal

if TYPE_CHECKING:
    from app.runtime.document_handles import LocalizedEvidenceHandle
    from app.runtime.tool_registry import ToolRegistry


@dataclass
class NodeHandle:
    node_id: str
    tools: ToolRegistry

    @property
    def node(self) -> IRNode:
        return self.tools.get_node(self.node_id)

    @property
    def kind(self) -> str:
        return self.node.kind

    @property
    def page_no(self) -> int | None:
        provenance = self.node.provenance
        return provenance.pdf_page if provenance is not None else None

    def text_content(self) -> str | None:
        node = self.node
        for attr in ("text", "caption", "text_repr", "title"):
            value = getattr(node, attr, None)
            if isinstance(value, str) and value:
                return value
        return None

    def localized_evidence(self, kind: str | None = None) -> list[LocalizedEvidenceHandle]:
        return self.tools.localized_evidence_for(self.node_id, kind=kind)

    def relations(self, kind: str | None = None) -> list[DocumentRelation]:
        return self.tools.relations_for(self.node_id, kind=kind)

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
