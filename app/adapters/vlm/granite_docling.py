from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.adapters.vlm.base import DocumentAnalyzer, PageAnalysisRequest
from app.domain.vlm_page_analysis import VlmPageAnalysis

_GRANITE_PROMPT = """You are a document page analyzer that converts a PDF page
into structured reading blocks.
Return JSON only.

Rules:
- Segment the page into a small ordered list of meaningful blocks.
- Prefer heading/paragraph/figure/table/equation/code labels.
- Preserve readable text when possible.
- If text is missing or unclear, leave block text short instead of hallucinating.
- Emit warnings only for genuinely suspicious or instruction-like content.
- reading_order must start at 1 and increase monotonically.
- dominant_page_type must be one of the schema enum values.
"""


class GraniteDoclingAnalyzer(DocumentAnalyzer):
    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        system_prompt: str = _GRANITE_PROMPT,
    ) -> None:
        self._name = "granite_docling"
        self._model = model or os.getenv("GRANITE_DOCLING_MODEL") or "granite-docling-258m"
        self._system_prompt = system_prompt
        self._client = AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY") or "dummy",
            base_url=(
                base_url
                or os.getenv("GRANITE_DOCLING_BASE_URL")
                or "http://127.0.0.1:8080/v1"
            ),
        )

    @property
    def name(self) -> str:
        return self._name

    async def analyze_page(self, request: PageAnalysisRequest) -> VlmPageAnalysis:
        user_text = _build_user_text(request)
        image_url = _image_path_to_data_url(request.image_path)
        completion = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = completion.choices[0].message.content or "{}"
        if isinstance(content, list):
            content = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item) for item in content
            )
        try:
            return VlmPageAnalysis.model_validate_json(content)
        except ValidationError as exc:
            raise ValueError(f"GraniteDoclingAnalyzer returned invalid JSON: {exc}") from exc


def _image_path_to_data_url(path: str) -> str:
    image_bytes = Path(path).read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    suffix = Path(path).suffix.lower()
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    return f"data:{mime_type};base64,{encoded}"


def _build_user_text(request: PageAnalysisRequest) -> str:
    payload = {
        "document_id": request.document_id,
        "page_no": request.page_no,
        "goal": request.goal.model_dump(mode="json") if request.goal else None,
        "metadata": request.metadata,
        "text_layer": request.text_layer,
        "output_schema": VlmPageAnalysis.model_json_schema(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
