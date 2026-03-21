from __future__ import annotations

import base64
import os
import time
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.adapters.vlm.base import DocumentAnalyzer, PageAnalysisRequest
from app.adapters.vlm.doctag_bridge import parse_granite_doctag_to_page_analysis
from app.domain.vlm_page_analysis import VlmPageAnalysis

_GRANITE_PROMPT = "Convert this page to docling."
_GRANITE_STOP = ["</doctag>", "<|end_of_text|>"]


class GraniteDoclingAnalyzer(DocumentAnalyzer):
    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        prompt: str = _GRANITE_PROMPT,
    ) -> None:
        self._name = "granite_docling"
        self._model = model or os.getenv("GRANITE_DOCLING_MODEL") or "granite-docling-258m"
        self._prompt = prompt
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
        start = time.perf_counter()
        completion = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _build_user_text(request, self._prompt)},
                        {
                            "type": "image_url",
                            "image_url": {"url": _image_path_to_data_url(request.image_path)},
                        },
                    ],
                }
            ],
            temperature=0.0,
            stop=_GRANITE_STOP,
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000)
        content = _coerce_completion_text(completion.choices[0].message.content)

        bridged = parse_granite_doctag_to_page_analysis(
            content,
            page_no=request.page_no,
            text_layer=request.text_layer,
        )
        if bridged is not None:
            bridged.notes.append("granite_native_doctag_mode")
            bridged.notes.append(f"granite_elapsed_ms={elapsed_ms}")
            bridged.notes.append(f"granite_model={self._model}")
            return bridged

        try:
            parsed = VlmPageAnalysis.model_validate_json(content)
        except ValidationError as exc:
            raise ValueError(f"GraniteDoclingAnalyzer returned unsupported payload: {exc}") from exc
        parsed.notes.append("granite_json_mode")
        parsed.notes.append(f"granite_elapsed_ms={elapsed_ms}")
        parsed.notes.append(f"granite_model={self._model}")
        return parsed


def _coerce_completion_text(content: str | list[object] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item) for item in content
        )
    return content


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


def _build_user_text(request: PageAnalysisRequest, prompt: str = _GRANITE_PROMPT) -> str:
    parts = [prompt]
    if request.goal and request.goal.user_query:
        parts.append(f"Reading goal: {request.goal.user_query}")
    if request.text_layer:
        parts.append(
            "Backend text layer is available and may be used only to recover "
            "readable text if needed."
        )
    return "\n".join(parts)
