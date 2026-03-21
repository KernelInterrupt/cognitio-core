from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adapters.vlm.granite_docling import GraniteDoclingAnalyzer, _build_user_text, _image_path_to_data_url
from app.adapters.vlm.base import PageAnalysisRequest
from app.domain.reading_goal import ReadingGoal
from app.ingest.pdf.extractor import PdfiumPageExtractor
from app.ingest.source import DocumentSource

async def main() -> None:
    source = DocumentSource.from_path('/home/pc/cognitio/experiments/attention_is_all_you_need.pdf')
    extracted = PdfiumPageExtractor().extract(source)
    first = extracted.pages[0]
    analyzer = GraniteDoclingAnalyzer(model='granite-docling-258M-Q8_0.gguf')
    user_text = _build_user_text(
        PageAnalysisRequest(
            document_id=extracted.document_id,
            page_no=1,
            image_path=first.image_path,
            text_layer=first.text_layer,
            goal=ReadingGoal(user_query='阅读这篇论文，重点关注核心方法、模型结构与训练细节。'),
            metadata=extracted.metadata,
        )
    )
    image_url = _image_path_to_data_url(first.image_path)
    completion = await analyzer._client.chat.completions.create(
        model='granite-docling-258M-Q8_0.gguf',
        messages=[
            {'role': 'system', 'content': analyzer._system_prompt},
            {'role': 'user', 'content': [
                {'type': 'text', 'text': user_text},
                {'type': 'image_url', 'image_url': {'url': image_url}},
            ]},
        ],
        temperature=0.1,
    )
    content = completion.choices[0].message.content
    print(type(content))
    print(content)

if __name__ == '__main__':
    asyncio.run(main())
