from __future__ import annotations

import os
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

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


class OpenAIProvider(ModelProvider):
    def __init__(
        self,
        model: str = "gpt-5-mini",
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise ModelProviderError("OPENAI_API_KEY is required for OpenAIProvider.")

        self._name = "openai"
        self._model = model
        self._client = AsyncOpenAI(api_key=resolved_key, base_url=base_url)

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_tools=True,
            supports_streaming=True,
            supports_structured_output=True,
            supports_openai_compatible_tools=True,
        )

    async def plan_reading(self, request: PlanRequest) -> PlanResponse:
        response = await self._client.responses.parse(
            model=self._model,
            instructions=request.system_prompt,
            input=request.model_dump_json(indent=2),
            text_format=PlanResponse,
        )
        return response.output_parsed

    async def guided_step(self, request: GuidedStepRequest) -> GuidedStepResponse:
        response = await self._client.responses.parse(
            model=self._model,
            instructions=request.system_prompt
            or (
                "You are a guided-reading runtime. Return only structured actions. "
                "Prefer sparse highlighting and minimal annotations."
            ),
            input=request.model_dump_json(indent=2),
            text_format=GuidedStepResponse,
        )
        return response.output_parsed

    async def edit_annotation(self, request: AnnotationEditRequest) -> AnnotationEditResponse:
        response = await self._client.responses.parse(
            model=self._model,
            instructions=request.system_prompt,
            input=request.model_dump_json(indent=2),
            text_format=AnnotationEditResponse,
        )
        return response.output_parsed

    async def research_subtask(self, request: ResearchSubtaskRequest) -> ResearchSubtaskResponse:
        response = await self._client.responses.parse(
            model=self._model,
            instructions=request.system_prompt,
            input=request.model_dump_json(indent=2),
            text_format=ResearchSubtaskResponse,
        )
        return response.output_parsed

    async def stream_guided_step(self, request: GuidedStepRequest) -> AsyncIterator[ProviderEvent]:
        async with self._client.responses.stream(
            model=self._model,
            instructions=request.system_prompt
            or (
                "You are a guided-reading runtime. Return only structured actions. "
                "Prefer sparse highlighting and minimal annotations."
            ),
            input=request.model_dump_json(indent=2),
            text_format=GuidedStepResponse,
        ) as stream:
            async for event in stream:
                yield ProviderEvent(
                    type="message_delta" if "delta" in event.type else "completed",
                    payload={"event_type": event.type},
                )
