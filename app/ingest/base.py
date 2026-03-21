from __future__ import annotations

from abc import ABC, abstractmethod

from app.ingest.parsed_document import ParsedDocument
from app.ingest.source import DocumentSource


class IngestBackend(ABC):
    name: str

    @abstractmethod
    def sniff(self, source: DocumentSource) -> bool: ...

    @abstractmethod
    def ingest(self, source: DocumentSource) -> ParsedDocument: ...
