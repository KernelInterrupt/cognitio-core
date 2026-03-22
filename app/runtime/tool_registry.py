from __future__ import annotations

from app.document.navigator import DocumentNavigator
from app.domain.annotation import Annotation
from app.domain.document_ir import DocumentIR, DocumentRelation, IRNode, LocalizedEvidence
from app.domain.research import ResearchRequest
from app.domain.signals import Advice, HighlightState, WarningSignal
from app.runtime.document_handles import DocumentHandle, LocalizedEvidenceHandle
from app.runtime.node_handle import NodeHandle


class ToolRegistry:
    """Core tool bindings layered on top of a document navigator."""

    def __init__(self, document: DocumentIR | None = None) -> None:
        self._navigator: DocumentNavigator | None = None
        if document is not None:
            self.bind_document(document)

    @property
    def document_ir(self) -> DocumentIR | None:
        return self._navigator.document if self._navigator is not None else None

    def bind_document(self, document: DocumentIR) -> DocumentHandle:
        self._navigator = DocumentNavigator(document)
        return DocumentHandle(document=document, tools=self)

    def document(self) -> DocumentHandle:
        document = self._require_document()
        return DocumentHandle(document=document, tools=self)

    def select(self, node_id: str) -> NodeHandle:
        document = self.document_ir
        if document is not None and node_id not in document.nodes:
            raise KeyError(f"Unknown node id: {node_id}")
        return NodeHandle(node_id=node_id, tools=self)

    def select_first(
        self,
        *,
        kind: str | None = None,
        text_contains: str | None = None,
        page_no: int | None = None,
    ) -> NodeHandle | None:
        navigator = self._require_navigator()
        node_id = navigator.select_first_node_id(
            kind=kind,
            text_contains=text_contains,
            page_no=page_no,
        )
        return self.select(node_id) if node_id is not None else None

    def select_first_evidence(
        self,
        *,
        kind: str | None = None,
        text_contains: str | None = None,
        page_no: int | None = None,
    ) -> LocalizedEvidenceHandle | None:
        navigator = self._require_navigator()
        evidence_id = navigator.select_first_evidence_id(
            kind=kind,
            text_contains=text_contains,
            page_no=page_no,
        )
        if evidence_id is None:
            return None
        return LocalizedEvidenceHandle(evidence_id=evidence_id, tools=self)

    def get_node(self, node_id: str) -> IRNode:
        return self._require_navigator().get_node(node_id)

    def get_evidence(self, evidence_id: str) -> LocalizedEvidence:
        return self._require_navigator().get_evidence(evidence_id)

    def node_ids_on_page(self, page_no: int, kind: str | None = None) -> list[str]:
        return self._require_navigator().node_ids_on_page(page_no, kind)

    def evidence_ids_on_page(self, page_no: int, kind: str | None = None) -> list[str]:
        return self._require_navigator().evidence_ids_on_page(page_no, kind)

    def localized_evidence_for(
        self,
        node_id: str,
        kind: str | None = None,
    ) -> list[LocalizedEvidenceHandle]:
        evidence_ids = self._require_navigator().localized_evidence_ids_for(
            node_id,
            kind=kind,
        )
        return [
            LocalizedEvidenceHandle(evidence_id=evidence_id, tools=self)
            for evidence_id in evidence_ids
        ]

    def captions_of(self, target_id: str) -> list[NodeHandle]:
        node_ids = self._require_navigator().caption_node_ids_for(target_id)
        return [self.select(node_id) for node_id in node_ids]

    def nearby_paragraphs_of(self, target_id: str) -> list[NodeHandle]:
        node_ids = self._require_navigator().nearby_paragraph_node_ids_for(target_id)
        return [self.select(node_id) for node_id in node_ids]

    def relations_for(self, target_id: str, kind: str | None = None) -> list[DocumentRelation]:
        return self._require_navigator().relations_for(target_id, kind=kind)

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

    def research(self, node_id: str, goal: str, scope: str | None = None) -> ResearchRequest:
        return ResearchRequest(
            task_id=f"research_{node_id}",
            node_id=node_id,
            goal=goal,
            scope=scope,
        )

    def _require_document(self) -> DocumentIR:
        return self._require_navigator().document

    def _require_navigator(self) -> DocumentNavigator:
        if self._navigator is None:
            raise RuntimeError("No document bound to ToolRegistry")
        return self._navigator
