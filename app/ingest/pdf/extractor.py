from __future__ import annotations

import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field

from app.ingest.source import DocumentSource


class PdfPageAsset(BaseModel):
    page_no: int
    image_path: str
    text_layer: str | None = None
    width: float | None = None
    height: float | None = None


class PdfPageExtractResult(BaseModel):
    document_id: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    pages: list[PdfPageAsset] = Field(default_factory=list)


class PdfPageExtractor(ABC):
    @abstractmethod
    def extract(self, source: DocumentSource) -> PdfPageExtractResult: ...


class PdfiumPageExtractor(PdfPageExtractor):
    def __init__(self, *, scale: float = 2.0, output_dir: str | None = None) -> None:
        self.scale = scale
        self.output_dir = Path(output_dir) if output_dir else None

    def extract(self, source: DocumentSource) -> PdfPageExtractResult:
        if not source.path:
            raise ValueError("PDF extraction currently requires a filesystem path.")

        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise RuntimeError(
                "pypdfium2 is required for PDF page rendering. Install project PDF dependencies."
            ) from exc

        pdf = pdfium.PdfDocument(source.path)
        target_dir = self.output_dir or Path(
            tempfile.mkdtemp(prefix="cognitio_pdf_pages_")
        )
        target_dir.mkdir(parents=True, exist_ok=True)

        pages: list[PdfPageAsset] = []
        for index in range(len(pdf)):
            page = pdf[index]
            width, height = page.get_size()
            bitmap = page.render(scale=self.scale)
            image_path = target_dir / f"page_{index + 1:04d}.png"
            bitmap.to_pil().save(image_path)

            text_layer: str | None = None
            try:
                text_page = page.get_textpage()
                text_layer = text_page.get_text_range()
            except Exception:
                text_layer = None

            pages.append(
                PdfPageAsset(
                    page_no=index + 1,
                    image_path=str(image_path),
                    text_layer=text_layer,
                    width=width,
                    height=height,
                )
            )

        return PdfPageExtractResult(
            document_id=source.filename or Path(source.path).stem,
            metadata={"backend": "pdfium_page_extractor", "page_count": len(pages)},
            pages=pages,
        )
