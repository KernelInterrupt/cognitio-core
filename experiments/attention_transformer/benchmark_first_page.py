from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adapters.vlm.base import PageAnalysisRequest
from app.adapters.vlm.granite_docling import GraniteDoclingAnalyzer, _build_user_text, _image_path_to_data_url
from app.domain.reading_goal import ReadingGoal
from app.ingest.pdf.extractor import PdfiumPageExtractor
from app.ingest.source import DocumentSource

PDF_PATH = Path('/home/pc/cognitio/experiments/attention_is_all_you_need.pdf')
OUT_DIR = Path('/home/pc/cognitio/experiments/attention_transformer/output')
OUT_DIR.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    timings: dict[str, float] = {}

    t0 = time.perf_counter()
    source = DocumentSource.from_path(PDF_PATH)
    timings['source_prepare_s'] = time.perf_counter() - t0

    t1 = time.perf_counter()
    extracted = PdfiumPageExtractor().extract(source)
    timings['pdf_extract_all_pages_s'] = time.perf_counter() - t1

    first = extracted.pages[0]
    analyzer = GraniteDoclingAnalyzer(model='granite-docling-258M-Q8_0.gguf')
    request = PageAnalysisRequest(
        document_id=extracted.document_id,
        page_no=1,
        image_path=first.image_path,
        text_layer=first.text_layer,
        goal=ReadingGoal(user_query='阅读这篇论文，重点关注核心方法、模型结构与训练细节。'),
        metadata=extracted.metadata,
    )

    t2 = time.perf_counter()
    raw_output: str | None = None
    error: str | None = None
    try:
        analysis = await analyzer.analyze_page(request)
        result_payload = analysis.model_dump(mode='json')
    except Exception as exc:
        error = str(exc)
        result_payload = None
        completion = await analyzer._client.chat.completions.create(
            model='granite-docling-258M-Q8_0.gguf',
            messages=[
                {'role': 'system', 'content': analyzer._system_prompt},
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': _build_user_text(request)},
                        {'type': 'image_url', 'image_url': {'url': _image_path_to_data_url(first.image_path)}},
                    ],
                },
            ],
            temperature=0.1,
        )
        raw_output = completion.choices[0].message.content
    timings['granite_first_page_s'] = time.perf_counter() - t2

    summary = {
        'pdf_path': str(PDF_PATH),
        'page_count': len(extracted.pages),
        'first_page_image_path': first.image_path,
        'first_page_text_layer_chars': len(first.text_layer or ''),
        'timings': timings,
        'analysis_ok': result_payload is not None,
        'error': error,
        'result': result_payload,
        'raw_output_prefix': raw_output[:2000] if isinstance(raw_output, str) else raw_output,
    }

    (OUT_DIR / 'benchmark_first_page.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
