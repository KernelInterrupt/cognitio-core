from __future__ import annotations

from app.adapters.vlm import GraniteDoclingAnalyzer
from app.ingest.backends import PlainTextBackend
from app.ingest.pdf.backends import PdfVlmBackend
from app.ingest.router import IngestRouter


def build_default_router() -> IngestRouter:
    return IngestRouter(
        backends=[
            PdfVlmBackend(GraniteDoclingAnalyzer()),
            PlainTextBackend(),
        ]
    )
