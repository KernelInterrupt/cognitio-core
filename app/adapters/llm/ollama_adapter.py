from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.adapters.llm.base import ModelProvider, ModelProviderError
from app.adapters.llm.models import (
    AnnotationEditRequest,
    AnnotationEditResponse,
    GuidedStepRequest,
    GuidedStepResponse,
    PlanRequest,
    PlanResponse,
    ProviderCapabilities,
    ProviderEvent,
    ResearchSubtaskRequest,
    ResearchSubtaskResponse,
)
from app.adapters.llm.ollama_connectivity import (
    build_ollama_connectivity_hint,
    resolve_ollama_base_url,
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class OllamaProvider(ModelProvider):
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._name = "ollama"
        self._model = model or os.getenv("OLLAMA_LLM_MODEL")
        if not self._model:
            raise ValueError("OllamaProvider requires an explicit model or OLLAMA_LLM_MODEL.")
        self._base_url = resolve_ollama_base_url(base_url)
        self._client = client or httpx.AsyncClient(base_url=self._base_url, timeout=120.0)
        self._owns_client = client is None

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_tools=False,
            supports_streaming=False,
            supports_structured_output=True,
            supports_system_prompt=True,
            supports_openai_compatible_tools=False,
        )

    async def plan_reading(self, request: PlanRequest) -> PlanResponse:
        return await self._chat_with_schema(
            request.system_prompt,
            request.model_dump_json(indent=2),
            PlanResponse,
        )

    async def guided_step(self, request: GuidedStepRequest) -> GuidedStepResponse:
        return await self._chat_with_schema(
            request.system_prompt
            or (
                "You are a guided-reading runtime. Return only structured actions. "
                "Prefer sparse highlighting and minimal annotations."
            ),
            request.model_dump_json(indent=2),
            GuidedStepResponse,
        )

    async def edit_annotation(self, request: AnnotationEditRequest) -> AnnotationEditResponse:
        return await self._chat_with_schema(
            request.system_prompt,
            request.model_dump_json(indent=2),
            AnnotationEditResponse,
        )

    async def research_subtask(self, request: ResearchSubtaskRequest) -> ResearchSubtaskResponse:
        return await self._chat_with_schema(
            request.system_prompt,
            request.model_dump_json(indent=2),
            ResearchSubtaskResponse,
        )

    async def stream_guided_step(self, request: GuidedStepRequest) -> AsyncIterator[ProviderEvent]:
        response = await self.guided_step(request)
        yield ProviderEvent(
            type="completed",
            payload={"response": response.model_dump(mode="json")},
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _chat_with_schema(
        self,
        system_prompt: str,
        user_payload: str,
        schema_model: type[SchemaT],
    ) -> SchemaT:
        schema = schema_model.model_json_schema()
        prompt = (
            f"{system_prompt}\n\n"
            "Return JSON only. The JSON must validate against the provided schema."
        )
        try:
            response = await self._client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "stream": False,
                    "format": schema,
                    "options": {"temperature": 0},
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_payload},
                    ],
                },
            )
        except httpx.HTTPError as exc:
            raise ModelProviderError(
                build_ollama_connectivity_hint(self._base_url) + f" Root error: {exc}"
            ) from exc
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ModelProviderError(
                f"Ollama request failed with status {exc.response.status_code}: {exc.response.text}"
            ) from exc

        payload = response.json()
        content = payload.get("message", {}).get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise ModelProviderError("Ollama returned an empty structured response.")

        try:
            return schema_model.model_validate_json(content)
        except ValidationError as exc:
            raise ModelProviderError(
                f"Ollama returned invalid structured JSON for {schema_model.__name__}: {exc}"
            ) from exc
