from __future__ import annotations

from collections import defaultdict

from app.domain.annotation import Annotation
from app.domain.document_ir import DocumentIR, DocumentRelation, IRNode, LocalizedEvidence
from app.domain.research import ResearchRequest
from app.domain.signals import Advice, HighlightState, WarningSignal
from app.runtime.document_handles import DocumentHandle, LocalizedEvidenceHandle
from app.runtime.node_handle import NodeHandle

CAPTION_RELATION_KINDS = {
    "caption_of_figure",
    "caption_of_table",
    "caption_of_equation",
}

NEARBY_RELATION_KINDS = {
    "nearby_paragraph_for_figure",
    "nearby_paragraph_for_table",
    "nearby_paragraph_for_equation",
}


class ToolRegistry:
    """Structured tool bindings plus a document runtime over finalized IR."""

    def __init__(self, document: DocumentIR | None = None) -> None:
        self.document_ir: DocumentIR | None = None
        self._node_ids_by_page: dict[int, list[str]] = {}
        self._evidence_ids_by_page: dict[int, list[str]] = {}
        self._outgoing_relations: dict[str, list[DocumentRelation]] = {}
        self._incoming_relations: dict[str, list[DocumentRelation]] = {}
        if document is not None:
            self.bind_document(document)

    def bind_document(self, document: DocumentIR) -> DocumentHandle:
        self.document_ir = document
        node_ids_by_page: dict[int, list[str]] = defaultdict(list)
        evidence_ids_by_page: dict[int, list[str]] = defaultdict(list)
        outgoing_relations: dict[str, list[DocumentRelation]] = defaultdict(list)
        incoming_relations: dict[str, list[DocumentRelation]] = defaultdict(list)

        for node_id, node in document.nodes.items():
            if node_id == document.root_id:
                continue
            page_no = self._page_for_node(node)
            if page_no is not None:
                node_ids_by_page[page_no].append(node_id)

        for evidence_id, evidence in document.localized_evidence.items():
            if evidence.page_no is not None:
                evidence_ids_by_page[evidence.page_no].append(evidence_id)

        for relation in document.relations:
            outgoing_relations[relation.source_id].append(relation)
            incoming_relations[relation.target_id].append(relation)

        self._node_ids_by_page = {
            page_no: sorted(ids, key=lambda node_id: document.nodes[node_id].order_index)
            for page_no, ids in node_ids_by_page.items()
        }
        self._evidence_ids_by_page = {
            page_no: sorted(
                ids,
                key=lambda evidence_id: document.localized_evidence[evidence_id].reading_order,
            )
            for page_no, ids in evidence_ids_by_page.items()
        }
        self._outgoing_relations = dict(outgoing_relations)
        self._incoming_relations = dict(incoming_relations)
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
        document = self._require_document()
        needle = text_contains.casefold() if text_contains is not None else None
        for node_id in document.reading_order:
            node = document.nodes[node_id]
            if page_no is not None and self._page_for_node(node) != page_no:
                continue
            if kind is not None and node.kind != kind:
                continue
            if needle is not None:
                haystack = self._node_text(node)
                if haystack is None or needle not in haystack.casefold():
                    continue
            return self.select(node_id)
        return None

    def select_first_evidence(
        self,
        *,
        kind: str | None = None,
        text_contains: str | None = None,
        page_no: int | None = None,
    ) -> LocalizedEvidenceHandle | None:
        document = self._require_document()
        needle = text_contains.casefold() if text_contains is not None else None
        evidence_ids = document.localized_evidence.keys()
        for evidence_id in evidence_ids:
            evidence = document.localized_evidence[evidence_id]
            if page_no is not None and evidence.page_no != page_no:
                continue
            if kind is not None and evidence.kind != kind:
                continue
            if needle is not None and needle not in evidence.text.casefold():
                continue
            return LocalizedEvidenceHandle(evidence_id=evidence_id, tools=self)
        return None

    def get_node(self, node_id: str) -> IRNode:
        document = self._require_document()
        return document.nodes[node_id]

    def get_evidence(self, evidence_id: str) -> LocalizedEvidence:
        document = self._require_document()
        return document.localized_evidence[evidence_id]

    def node_ids_on_page(self, page_no: int, kind: str | None = None) -> list[str]:
        document = self._require_document()
        node_ids = self._node_ids_by_page.get(page_no, [])
        if kind is None:
            return list(node_ids)
        return [node_id for node_id in node_ids if document.nodes[node_id].kind == kind]

    def evidence_ids_on_page(self, page_no: int, kind: str | None = None) -> list[str]:
        document = self._require_document()
        evidence_ids = self._evidence_ids_by_page.get(page_no, [])
        if kind is None:
            return list(evidence_ids)
        return [
            evidence_id
            for evidence_id in evidence_ids
            if document.localized_evidence[evidence_id].kind == kind
        ]

    def localized_evidence_for(
        self,
        node_id: str,
        kind: str | None = None,
    ) -> list[LocalizedEvidenceHandle]:
        document = self._require_document()
        handles: list[LocalizedEvidenceHandle] = []
        for relation in self._incoming_relations.get(node_id, []):
            if relation.kind != "localized_evidence_for_block":
                continue
            evidence = document.localized_evidence.get(relation.source_id)
            if evidence is None:
                continue
            if kind is not None and evidence.kind != kind:
                continue
            handles.append(LocalizedEvidenceHandle(evidence_id=evidence.id, tools=self))
        return handles

    def captions_of(self, target_id: str) -> list[NodeHandle]:
        return [
            self.select(relation.source_id)
            for relation in self._incoming_relations.get(target_id, [])
            if relation.kind in CAPTION_RELATION_KINDS and self._is_node_id(relation.source_id)
        ]

    def nearby_paragraphs_of(self, target_id: str) -> list[NodeHandle]:
        return [
            self.select(relation.target_id)
            for relation in self._outgoing_relations.get(target_id, [])
            if relation.kind in NEARBY_RELATION_KINDS and self._is_node_id(relation.target_id)
        ]

    def relations_for(self, target_id: str, kind: str | None = None) -> list[DocumentRelation]:
        relations = [
            *self._outgoing_relations.get(target_id, []),
            *self._incoming_relations.get(target_id, []),
        ]
        if kind is None:
            return relations
        return [relation for relation in relations if relation.kind == kind]

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
        if self.document_ir is None:
            raise RuntimeError("No document bound to ToolRegistry")
        return self.document_ir

    def _is_node_id(self, item_id: str) -> bool:
        document = self._require_document()
        return item_id in document.nodes

    @staticmethod
    def _page_for_node(node: IRNode) -> int | None:
        provenance = node.provenance
        return provenance.pdf_page if provenance is not None else None

    @staticmethod
    def _node_text(node: IRNode) -> str | None:
        for attr in ("text", "caption", "text_repr", "title"):
            value = getattr(node, attr, None)
            if isinstance(value, str) and value:
                return value
        return None
