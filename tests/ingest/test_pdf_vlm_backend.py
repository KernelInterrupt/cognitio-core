import asyncio

from app.adapters.vlm.base import DocumentAnalyzer, PageAnalysisRequest
from app.domain.document_ir import ParagraphNode, SectionNode
from app.domain.reading_goal import ReadingGoal
from app.domain.vlm_page_analysis import VlmPageAnalysis, VlmPageBlock
from app.ingest.pdf.backends import PdfVlmBackend
from app.ingest.pdf.extractor import PdfPageAsset, PdfPageExtractor, PdfPageExtractResult
from app.ingest.source import DocumentSource


class FakeExtractor(PdfPageExtractor):
    def extract(self, source: DocumentSource) -> PdfPageExtractResult:
        return PdfPageExtractResult(
            document_id="sample",
            metadata={"title": "Sample PDF"},
            pages=[
                PdfPageAsset(
                    page_no=1,
                    image_path="/tmp/page1.png",
                    text_layer="Introduction\n\nThis is the first paragraph.",
                    width=100,
                    height=200,
                )
            ],
        )


class FakeAnalyzer(DocumentAnalyzer):
    @property
    def name(self) -> str:
        return "fake_granite"

    async def analyze_page(self, request: PageAnalysisRequest) -> VlmPageAnalysis:
        return VlmPageAnalysis(
            page_no=request.page_no,
            dominant_page_type="paper_body",
            blocks=[
                VlmPageBlock(kind="heading", text="Introduction", reading_order=1),
                VlmPageBlock(
                    kind="paragraph",
                    text="This is the first paragraph.",
                    reading_order=2,
                ),
            ],
        )


class EmptyAnalyzer(DocumentAnalyzer):
    @property
    def name(self) -> str:
        return "empty"

    async def analyze_page(self, request: PageAnalysisRequest) -> VlmPageAnalysis:
        return VlmPageAnalysis(page_no=request.page_no)


def test_pdf_vlm_backend_converts_analysis_into_ir() -> None:
    backend = PdfVlmBackend(FakeAnalyzer(), extractor=FakeExtractor())
    source = DocumentSource(
        path="/tmp/sample.pdf",
        filename="sample.pdf",
        media_type="application/pdf",
    )

    document = asyncio.run(backend.parse_pdf_to_ir(source, goal=ReadingGoal(user_query="读论文")))

    first_node = document.nodes[document.reading_order[0]]
    second_node = document.nodes[document.reading_order[1]]
    assert isinstance(first_node, SectionNode)
    assert isinstance(second_node, ParagraphNode)
    assert second_node.text == "This is the first paragraph."
    assert document.metadata.source_kind == "pdf"


def test_pdf_vlm_backend_falls_back_to_text_layer_when_analysis_empty() -> None:
    backend = PdfVlmBackend(EmptyAnalyzer(), extractor=FakeExtractor())
    source = DocumentSource(
        path="/tmp/sample.pdf",
        filename="sample.pdf",
        media_type="application/pdf",
    )

    parsed = asyncio.run(backend.aingest(source))

    assert parsed.pages[0].blocks
    assert parsed.pages[0].blocks[0].text.startswith("Introduction")
