from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adapters.vlm.granite_docling import GraniteDoclingAnalyzer
from app.domain.reading_goal import ReadingGoal
from app.ingest.pdf.backends import PdfVlmBackend
from app.ingest.source import DocumentSource

PDF_PATH = Path('/home/pc/cognitio/experiments/attention_is_all_you_need.pdf')
OUT_DIR = Path('/home/pc/cognitio/experiments/attention_transformer/output')
OUT_DIR.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    analyzer = GraniteDoclingAnalyzer(model='granite-docling-258M-Q8_0.gguf')
    backend = PdfVlmBackend(analyzer)
    source = DocumentSource.from_path(PDF_PATH)
    goal = ReadingGoal(user_query='阅读这篇论文，重点关注核心方法、模型结构与训练细节。')

    parsed = await backend.aingest(source, goal=goal)
    ir = backend.normalizer.normalize(parsed)

    (OUT_DIR / 'parsed_document.json').write_text(
        parsed.model_dump_json(indent=2),
        encoding='utf-8',
    )
    (OUT_DIR / 'document_ir.json').write_text(
        ir.model_dump_json(indent=2),
        encoding='utf-8',
    )

    summary = {
        'document_id': ir.document_id,
        'source_kind': ir.metadata.source_kind,
        'node_count': len(ir.nodes),
        'reading_order_count': len(ir.reading_order),
        'first_nodes': [
            {
                'id': node_id,
                'kind': ir.nodes[node_id].kind,
                'text': getattr(ir.nodes[node_id], 'text', None),
                'title': getattr(ir.nodes[node_id], 'title', None),
            }
            for node_id in ir.reading_order[:12]
        ],
    }
    (OUT_DIR / 'summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
