from __future__ import annotations

from collections import defaultdict

from app.domain.document_ir import DocumentIR, DocumentRelation, IRNode, LocalizedEvidence

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


class DocumentNavigator:
    """Pure document-side querying over finalized DocumentIR.

    This class deliberately contains no highlight/annotation/research behavior.
    It only answers structural questions about the document.
    """

    def __init__(self, document: DocumentIR) -> None:
        self.document = document
        node_ids_by_page: dict[int, list[str]] = defaultdict(list)
        evidence_ids_by_page: dict[int, list[str]] = defaultdict(list)
        outgoing_relations: dict[str, list[DocumentRelation]] = defaultdict(list)
        incoming_relations: dict[str, list[DocumentRelation]] = defaultdict(list)

        for node_id, node in document.nodes.items():
            if node_id == document.root_id:
                continue
            page_no = self.page_for_node(node)
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

    def get_node(self, node_id: str) -> IRNode:
        return self.document.nodes[node_id]

    def get_evidence(self, evidence_id: str) -> LocalizedEvidence:
        return self.document.localized_evidence[evidence_id]

    def node_ids_on_page(self, page_no: int, kind: str | None = None) -> list[str]:
        node_ids = self._node_ids_by_page.get(page_no, [])
        if kind is None:
            return list(node_ids)
        return [node_id for node_id in node_ids if self.document.nodes[node_id].kind == kind]

    def evidence_ids_on_page(self, page_no: int, kind: str | None = None) -> list[str]:
        evidence_ids = self._evidence_ids_by_page.get(page_no, [])
        if kind is None:
            return list(evidence_ids)
        return [
            evidence_id
            for evidence_id in evidence_ids
            if self.document.localized_evidence[evidence_id].kind == kind
        ]

    def select_first_node_id(
        self,
        *,
        kind: str | None = None,
        text_contains: str | None = None,
        page_no: int | None = None,
    ) -> str | None:
        needle = text_contains.casefold() if text_contains is not None else None
        for node_id in self.document.reading_order:
            node = self.document.nodes[node_id]
            if page_no is not None and self.page_for_node(node) != page_no:
                continue
            if kind is not None and node.kind != kind:
                continue
            if needle is not None:
                haystack = self.node_text(node)
                if haystack is None or needle not in haystack.casefold():
                    continue
            return node_id
        return None

    def select_first_evidence_id(
        self,
        *,
        kind: str | None = None,
        text_contains: str | None = None,
        page_no: int | None = None,
    ) -> str | None:
        needle = text_contains.casefold() if text_contains is not None else None
        for evidence_id, evidence in self.document.localized_evidence.items():
            if page_no is not None and evidence.page_no != page_no:
                continue
            if kind is not None and evidence.kind != kind:
                continue
            if needle is not None and needle not in evidence.text.casefold():
                continue
            return evidence_id
        return None

    def localized_evidence_ids_for(
        self,
        node_id: str,
        kind: str | None = None,
    ) -> list[str]:
        evidence_ids: list[str] = []
        for relation in self._incoming_relations.get(node_id, []):
            if relation.kind != "localized_evidence_for_block":
                continue
            evidence = self.document.localized_evidence.get(relation.source_id)
            if evidence is None:
                continue
            if kind is not None and evidence.kind != kind:
                continue
            evidence_ids.append(evidence.id)
        return evidence_ids

    def caption_node_ids_for(self, target_id: str) -> list[str]:
        return [
            relation.source_id
            for relation in self._incoming_relations.get(target_id, [])
            if relation.kind in CAPTION_RELATION_KINDS and self.is_node_id(relation.source_id)
        ]

    def nearby_paragraph_node_ids_for(self, target_id: str) -> list[str]:
        return [
            relation.target_id
            for relation in self._outgoing_relations.get(target_id, [])
            if relation.kind in NEARBY_RELATION_KINDS and self.is_node_id(relation.target_id)
        ]

    def relations_for(self, item_id: str, kind: str | None = None) -> list[DocumentRelation]:
        relations = [
            *self._outgoing_relations.get(item_id, []),
            *self._incoming_relations.get(item_id, []),
        ]
        if kind is None:
            return relations
        return [relation for relation in relations if relation.kind == kind]

    def is_node_id(self, item_id: str) -> bool:
        return item_id in self.document.nodes

    @staticmethod
    def page_for_node(node: IRNode) -> int | None:
        provenance = node.provenance
        return provenance.pdf_page if provenance is not None else None

    @staticmethod
    def node_text(node: IRNode) -> str | None:
        for attr in ("text", "caption", "text_repr", "title"):
            value = getattr(node, attr, None)
            if isinstance(value, str) and value:
                return value
        return None
