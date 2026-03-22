from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod

from app.adapters.vlm.base import DocumentAnalyzer, PageAnalysisRequest
from app.domain.document_ir import DocumentIR
from app.domain.reading_goal import ReadingGoal
from app.domain.vlm_page_analysis import VlmPageAnalysis, VlmPageBlock
from app.ingest.backends.plain_text import PlainTextBackend
from app.ingest.base import IngestBackend
from app.ingest.normalizer import ParsedDocumentNormalizer
from app.ingest.parsed_document import ParsedBlock, ParsedDocument, ParsedPage, ParsedRelation
from app.ingest.pdf.extractor import PdfiumPageExtractor, PdfPageExtractor
from app.ingest.source import DocumentSource


class PdfIrBackend(ABC):
    name: str

    @abstractmethod
    async def parse_pdf_to_ir(
        self,
        source: DocumentSource,
        *,
        goal: ReadingGoal | None = None,
    ) -> DocumentIR: ...


class PdfVlmBackend(IngestBackend, PdfIrBackend):
    name = "pdf_vlm"

    def __init__(
        self,
        analyzer: DocumentAnalyzer,
        *,
        extractor: PdfPageExtractor | None = None,
        normalizer: ParsedDocumentNormalizer | None = None,
    ) -> None:
        self.analyzer = analyzer
        self.extractor = extractor or PdfiumPageExtractor()
        self.normalizer = normalizer or ParsedDocumentNormalizer()

    def sniff(self, source: DocumentSource) -> bool:
        return (source.media_type or "") == "application/pdf"

    def ingest(self, source: DocumentSource) -> ParsedDocument:
        return asyncio.run(self.aingest(source))

    async def aingest(
        self,
        source: DocumentSource,
        *,
        goal: ReadingGoal | None = None,
    ) -> ParsedDocument:
        extracted = self.extractor.extract(source)
        pages: list[ParsedPage] = []
        for asset in extracted.pages:
            analysis_error: str | None = None
            try:
                analysis = await self.analyzer.analyze_page(
                    PageAnalysisRequest(
                        document_id=extracted.document_id,
                        page_no=asset.page_no,
                        image_path=asset.image_path,
                        text_layer=asset.text_layer,
                        goal=goal,
                        metadata=extracted.metadata,
                    )
                )
            except Exception as exc:
                analysis = VlmPageAnalysis(
                    page_no=asset.page_no,
                    notes=[f"analyzer_error: {exc}"],
                )
                analysis_error = str(exc)

            primary_blocks, localized_evidence = _split_blocks_by_layer(
                asset.page_no,
                analysis.blocks,
                backend_name=self.name,
                analyzer_name=self.analyzer.name,
            )
            relations = _build_relations(asset.page_no, primary_blocks, localized_evidence)
            page = ParsedPage(
                page_no=asset.page_no,
                width=asset.width,
                height=asset.height,
                image_path=asset.image_path,
                text_layer=asset.text_layer,
                blocks=primary_blocks,
                localized_evidence=localized_evidence,
                relations=relations,
            )
            if not page.blocks and asset.text_layer and asset.text_layer.strip():
                page.blocks = _fallback_blocks_from_text(asset.page_no, asset.text_layer)
                if analysis_error:
                    for block in page.blocks:
                        block.provenance["analyzer_error"] = analysis_error
            pages.append(page)

        localized_evidence_count = sum(len(page.localized_evidence) for page in pages)
        relation_count = sum(len(page.relations) for page in pages)
        return ParsedDocument(
            document_id=extracted.document_id,
            source_kind="pdf",
            metadata={
                **extracted.metadata,
                "backend": self.name,
                "analyzer": self.analyzer.name,
                "localized_evidence_count": localized_evidence_count,
                "relation_count": relation_count,
            },
            pages=pages,
        )

    async def parse_pdf_to_ir(
        self,
        source: DocumentSource,
        *,
        goal: ReadingGoal | None = None,
    ) -> DocumentIR:
        parsed = await self.aingest(source, goal=goal)
        return self.normalizer.normalize(parsed)


def _global_reading_order(page_no: int, local_order: int) -> int:
    return page_no * 10_000 + local_order


def _fallback_blocks_from_text(page_no: int, text_layer: str) -> list[ParsedBlock]:
    chunks = [chunk.strip() for chunk in text_layer.split("\n\n") if chunk.strip()]
    if not chunks:
        chunks = [line.strip() for line in text_layer.splitlines() if line.strip()]
    return [
        ParsedBlock(
            block_id=f"p{page_no:04d}_fallback_{index:04d}",
            kind="paragraph",
            text=chunk,
            page_no=page_no,
            reading_order=_global_reading_order(page_no, index),
            provenance={"backend": PlainTextBackend.name, "fallback": True},
        )
        for index, chunk in enumerate(chunks, start=1)
    ]


def _split_blocks_by_layer(
    page_no: int,
    blocks: list[VlmPageBlock],
    *,
    backend_name: str,
    analyzer_name: str,
) -> tuple[list[ParsedBlock], list[ParsedBlock]]:
    primary: list[ParsedBlock] = []
    localized_evidence: list[ParsedBlock] = []
    for block in blocks:
        parsed = ParsedBlock(
            block_id=f"p{page_no:04d}_b{block.reading_order:04d}",
            kind=block.kind,
            text=block.text,
            page_no=page_no,
            bbox=block.bbox,
            reading_order=_global_reading_order(page_no, block.reading_order),
            provenance={
                "backend": backend_name,
                "analyzer": analyzer_name,
                "rationale": block.rationale,
                "layer": block.layer,
            },
        )
        if block.layer == "supporting":
            localized_evidence.append(parsed)
        else:
            primary.append(parsed)
    return primary, localized_evidence


def _build_relations(
    page_no: int,
    primary_blocks: list[ParsedBlock],
    localized_evidence: list[ParsedBlock],
) -> list[ParsedRelation]:
    relations: list[ParsedRelation] = []
    primary_text_blocks = [
        block for block in primary_blocks if block.kind in {"heading", "paragraph"}
    ]
    primary_paragraphs = [block for block in primary_blocks if block.kind == "paragraph"]

    for index, evidence in enumerate(localized_evidence, start=1):
        target = _match_evidence_to_primary_block(evidence, primary_text_blocks)
        if target is not None:
            relations.append(
                ParsedRelation(
                    relation_id=f"rel_{page_no:04d}_{index:04d}_evidence",
                    kind="localized_evidence_for_block",
                    source_block_id=evidence.block_id,
                    target_block_id=target.block_id,
                    score=_text_overlap_score(evidence.text, target.text),
                    provenance={"strategy": "text_overlap"},
                )
            )

        if evidence.kind not in {"figure", "table", "equation"}:
            continue

        caption_target = _find_caption_candidate(evidence, primary_paragraphs)
        relation_kind = {
            "figure": "caption_of_figure",
            "table": "caption_of_table",
            "equation": "caption_of_equation",
        }[evidence.kind]
        if caption_target is not None:
            relations.append(
                ParsedRelation(
                    relation_id=f"rel_{page_no:04d}_{index:04d}_caption",
                    kind=relation_kind,
                    source_block_id=caption_target.block_id,
                    target_block_id=evidence.block_id,
                    score=_distance_score(evidence.reading_order, caption_target.reading_order),
                    provenance={"strategy": "caption_candidate"},
                )
            )

        nearby_paragraph = _nearest_paragraph(evidence, primary_paragraphs)
        nearby_kind = {
            "figure": "nearby_paragraph_for_figure",
            "table": "nearby_paragraph_for_table",
            "equation": "nearby_paragraph_for_equation",
        }[evidence.kind]
        if nearby_paragraph is not None:
            relations.append(
                ParsedRelation(
                    relation_id=f"rel_{page_no:04d}_{index:04d}_nearby",
                    kind=nearby_kind,
                    source_block_id=evidence.block_id,
                    target_block_id=nearby_paragraph.block_id,
                    score=_distance_score(evidence.reading_order, nearby_paragraph.reading_order),
                    provenance={"strategy": "nearest_paragraph"},
                )
            )

    return relations


def _match_evidence_to_primary_block(
    evidence: ParsedBlock,
    primary_blocks: list[ParsedBlock],
) -> ParsedBlock | None:
    evidence_norm = _normalize_text(evidence.text)
    if not evidence_norm:
        return None

    best: ParsedBlock | None = None
    best_score = 0.0
    for block in primary_blocks:
        score = _text_overlap_score(evidence.text, block.text)
        if score > best_score:
            best = block
            best_score = score
    return best if best_score >= 0.35 else None


def _find_caption_candidate(
    evidence: ParsedBlock,
    primary_paragraphs: list[ParsedBlock],
) -> ParsedBlock | None:
    candidates: list[ParsedBlock] = []
    for paragraph in primary_paragraphs:
        norm = _normalize_text(paragraph.text)
        if not norm:
            continue
        if paragraph.reading_order < evidence.reading_order:
            continue
        if _looks_like_caption(paragraph.text):
            candidates.append(paragraph)
    if candidates:
        return min(candidates, key=lambda block: block.reading_order - evidence.reading_order)
    return None


def _nearest_paragraph(
    evidence: ParsedBlock,
    primary_paragraphs: list[ParsedBlock],
) -> ParsedBlock | None:
    if not primary_paragraphs:
        return None
    return min(
        primary_paragraphs,
        key=lambda block: abs(block.reading_order - evidence.reading_order),
    )


def _looks_like_caption(text: str) -> bool:
    norm = _normalize_text(text)
    return norm.startswith("figure ") or norm.startswith("fig. ") or norm.startswith("table ")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _text_overlap_score(a: str, b: str) -> float:
    a_norm = _normalize_text(a)
    b_norm = _normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    if a_norm in b_norm:
        return min(1.0, len(a_norm) / max(1, len(b_norm)))
    if b_norm in a_norm:
        return min(1.0, len(b_norm) / max(1, len(a_norm)))
    a_tokens = set(a_norm.split())
    b_tokens = set(b_norm.split())
    if not a_tokens or not b_tokens:
        return 0.0
    overlap = len(a_tokens & b_tokens)
    return overlap / max(1, min(len(a_tokens), len(b_tokens)))


def _distance_score(a: int, b: int) -> float:
    return 1.0 / (1 + abs(a - b))
