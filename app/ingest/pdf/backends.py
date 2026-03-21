from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from app.adapters.vlm.base import DocumentAnalyzer, PageAnalysisRequest
from app.domain.document_ir import DocumentIR
from app.domain.reading_goal import ReadingGoal
from app.domain.vlm_page_analysis import VlmPageAnalysis
from app.ingest.backends.plain_text import PlainTextBackend
from app.ingest.base import IngestBackend
from app.ingest.normalizer import ParsedDocumentNormalizer
from app.ingest.parsed_document import ParsedBlock, ParsedDocument, ParsedPage
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

            page = ParsedPage(
                page_no=asset.page_no,
                width=asset.width,
                height=asset.height,
                image_path=asset.image_path,
                text_layer=asset.text_layer,
                blocks=[
                    ParsedBlock(
                        block_id=f"p{asset.page_no:04d}_b{block.reading_order:04d}",
                        kind=block.kind,
                        text=block.text,
                        page_no=asset.page_no,
                        bbox=block.bbox,
                        reading_order=_global_reading_order(asset.page_no, block.reading_order),
                        provenance={
                            "backend": self.name,
                            "analyzer": self.analyzer.name,
                            "rationale": block.rationale,
                        },
                    )
                    for block in analysis.blocks
                ],
            )
            if not page.blocks and asset.text_layer and asset.text_layer.strip():
                page.blocks = _fallback_blocks_from_text(asset.page_no, asset.text_layer)
                if analysis_error:
                    for block in page.blocks:
                        block.provenance["analyzer_error"] = analysis_error
            pages.append(page)

        return ParsedDocument(
            document_id=extracted.document_id,
            source_kind="pdf",
            metadata={
                **extracted.metadata,
                "backend": self.name,
                "analyzer": self.analyzer.name,
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
