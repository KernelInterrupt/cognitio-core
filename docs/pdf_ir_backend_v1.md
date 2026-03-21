# PDF -> IR Backend v1

## Decision

Current default path:

- **PDF -> page images + optional text layer**
- **Granite-Docling VLM analyzes each page**
- **analysis is normalized into `DocumentIR`**
- stronger reading models (GPT/Gemini/etc.) run only after IR exists

## Main interfaces

### `DocumentAnalyzer`
Defined in `app/adapters/vlm/base.py`.

```python
class DocumentAnalyzer(ABC):
    async def analyze_page(self, request: PageAnalysisRequest) -> VlmPageAnalysis: ...
```

This is the upgrade point for future page-understanding models.

Current implementation:
- `GraniteDoclingAnalyzer`

Future implementations can include:
- GPT-based page analyzer
- Gemini-based page analyzer
- Qwen-VL page analyzer
- hybrid analyzers

### `PdfIrBackend`
Defined in `app/ingest/pdf/backends.py`.

```python
class PdfIrBackend(ABC):
    async def parse_pdf_to_ir(self, source, *, goal=None) -> DocumentIR: ...
```

Current implementation:
- `PdfVlmBackend`

This is the upgrade point for future PDF ingestion strategies.

### `PdfPageExtractor`
Defined in `app/ingest/pdf/extractor.py`.

```python
class PdfPageExtractor(ABC):
    def extract(self, source) -> PdfPageExtractResult: ...
```

Current implementation:
- `PdfiumPageExtractor`

This layer is intentionally thin. It should only provide:
- page image paths
- optional text layer
- page size metadata

## Current default stack

- extractor: `PdfiumPageExtractor`
- analyzer: `GraniteDoclingAnalyzer`
- backend: `PdfVlmBackend`
- router factory: `build_default_router()`

## Upgrade policy

When replacing the page-understanding model, do **not** change:
- `DocumentIR`
- runtime orchestration
- node handle API
- annotation sandbox protocol

Only swap:
- `DocumentAnalyzer` implementation
- optionally `PdfPageExtractor`
- optionally `PdfIrBackend`

## Environment knobs

`GraniteDoclingAnalyzer` currently reads:
- `GRANITE_DOCLING_BASE_URL`
- `GRANITE_DOCLING_MODEL`
- `OPENAI_API_KEY` (falls back to dummy for local OpenAI-compatible servers)

## Non-goals for v1

- perfect publisher-grade PDF reconstruction
- heavy parser-first pipelines
- Torch/ONNX default dependency chain
- tying guided reading to a specific page-analysis model
