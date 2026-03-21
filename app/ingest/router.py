from __future__ import annotations

import asyncio

from app.domain.document_ir import DocumentIR
from app.domain.reading_goal import ReadingGoal
from app.ingest.backends import PlainTextBackend
from app.ingest.base import IngestBackend
from app.ingest.normalizer import ParsedDocumentNormalizer
from app.ingest.parsed_document import ParsedDocument
from app.ingest.pdf.backends import PdfVlmBackend
from app.ingest.source import DocumentSource


class IngestRouter:
    def __init__(
        self,
        backends: list[IngestBackend] | None = None,
        normalizer: ParsedDocumentNormalizer | None = None,
    ) -> None:
        self.backends = backends or [PlainTextBackend()]
        self.normalizer = normalizer or ParsedDocumentNormalizer()

    def ingest(self, source: DocumentSource) -> ParsedDocument:
        return asyncio.run(self.aingest(source))

    async def aingest(
        self,
        source: DocumentSource,
        *,
        goal: ReadingGoal | None = None,
    ) -> ParsedDocument:
        for backend in self.backends:
            if not backend.sniff(source):
                continue
            if isinstance(backend, PdfVlmBackend):
                return await backend.aingest(source, goal=goal)
            return backend.ingest(source)
        raise ValueError(f"No ingest backend matched source: media_type={source.media_type!r}")

    def ingest_to_ir(self, source: DocumentSource) -> DocumentIR:
        return asyncio.run(self.aingest_to_ir(source))

    async def aingest_to_ir(
        self,
        source: DocumentSource,
        *,
        goal: ReadingGoal | None = None,
    ) -> DocumentIR:
        parsed = await self.aingest(source, goal=goal)
        return self.normalizer.normalize(parsed)
