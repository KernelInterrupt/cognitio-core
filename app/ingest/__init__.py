"""Thin ingestion layer for VLM-first guided reading."""

from app.ingest.normalizer import ParsedDocumentNormalizer
from app.ingest.pdf import PdfIrBackend, PdfiumPageExtractor, PdfVlmBackend
from app.ingest.router import IngestRouter
from app.ingest.source import DocumentSource

__all__ = [
    "DocumentSource",
    "IngestRouter",
    "ParsedDocumentNormalizer",
    "PdfIrBackend",
    "PdfVlmBackend",
    "PdfiumPageExtractor",
]
