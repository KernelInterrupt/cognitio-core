from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.adapters.llm.models import (
    AnnotationEditRequest,
    AnnotationEditResponse,
    GuidedStepRequest,
    GuidedStepResponse,
    PlanRequest,
    PlanResponse,
    ProviderCapabilities,
    ProviderEvent,
)


class ModelProviderError(RuntimeError):
    """Raised when a provider cannot fulfill a request."""


class ModelProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: ...

    @abstractmethod
    async def plan_reading(self, request: PlanRequest) -> PlanResponse: ...

    @abstractmethod
    async def guided_step(self, request: GuidedStepRequest) -> GuidedStepResponse: ...

    @abstractmethod
    async def edit_annotation(self, request: AnnotationEditRequest) -> AnnotationEditResponse: ...

    async def stream_guided_step(self, request: GuidedStepRequest) -> AsyncIterator[ProviderEvent]:
        response = await self.guided_step(request)
        yield ProviderEvent(
            type="completed",
            payload={"response": response.model_dump(mode="json")},
        )
