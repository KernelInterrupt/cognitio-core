from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from app.domain.reading_goal import ReadingGoal
from app.domain.vlm_page_analysis import VlmPageAnalysis


class PageAnalysisRequest(BaseModel):
    document_id: str
    page_no: int
    image_path: str
    text_layer: str | None = None
    goal: ReadingGoal | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class DocumentAnalyzer(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def analyze_page(self, request: PageAnalysisRequest) -> VlmPageAnalysis: ...
