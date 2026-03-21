from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from app.domain.annotation import CompileError
from app.domain.document_ir import DocumentIR
from app.domain.reading_goal import ReadingGoal, UserIntervention
from app.domain.research import ResearchFinding


class ProviderCapabilities(BaseModel):
    supports_tools: bool = False
    supports_streaming: bool = False
    supports_structured_output: bool = False
    supports_system_prompt: bool = True
    supports_openai_compatible_tools: bool = False
    max_context_tokens: int | None = None


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)


class PlanRequest(BaseModel):
    document_ir: DocumentIR
    goal: ReadingGoal
    system_prompt: str
    user_notes: list[str] = Field(default_factory=list)


class PlanResponse(BaseModel):
    reading_mode: str
    key_nodes: list[str] = Field(default_factory=list)
    skip_hints: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GuidedStepRequest(BaseModel):
    document_id: str
    node_id: str
    current_node_text: str
    system_prompt: str | None = None
    local_context_before: list[str] = Field(default_factory=list)
    local_context_after: list[str] = Field(default_factory=list)
    reading_mode: str
    goal: ReadingGoal
    plan_summary: str | None = None
    key_nodes: list[str] = Field(default_factory=list)
    available_tools: list[ToolSpec] = Field(default_factory=list)
    user_interventions: list[UserIntervention] = Field(default_factory=list)


class HighlightAction(BaseModel):
    type: Literal["highlight"] = "highlight"
    level: Literal["skip", "normal", "important", "critical"]
    reason: str | None = None


class WarningAction(BaseModel):
    type: Literal["warning"] = "warning"
    kind: str
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    evidence: list[str] = Field(default_factory=list)


class AdviceAction(BaseModel):
    type: Literal["advice"] = "advice"
    kind: str
    message: str
    basis: list[str] = Field(default_factory=list)


class OpenAnnotationAction(BaseModel):
    type: Literal["open_annotation"] = "open_annotation"
    annotation_type: Literal["summary", "intuition", "critique", "highlight"]
    language: str = "zh"


class ResearchAction(BaseModel):
    type: Literal["research"] = "research"
    goal: str
    scope: str | None = None


class NextAction(BaseModel):
    type: Literal["next"] = "next"


ModelAction = Annotated[
    HighlightAction
    | WarningAction
    | AdviceAction
    | OpenAnnotationAction
    | ResearchAction
    | NextAction,
    Field(discriminator="type"),
]


class GuidedStepResponse(BaseModel):
    actions: list[ModelAction] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AnnotationEditRequest(BaseModel):
    annotation_id: str
    target_node_id: str
    annotation_type: str
    language: str
    current_file: str
    editable_region: str
    compile_errors: list[CompileError] = Field(default_factory=list)
    system_prompt: str


class WriteFileAction(BaseModel):
    type: Literal["write_file"] = "write_file"
    content: str


class PatchFileAction(BaseModel):
    type: Literal["patch_file"] = "patch_file"
    old: str
    new: str


class CompileAction(BaseModel):
    type: Literal["compile"] = "compile"


class SubmitAction(BaseModel):
    type: Literal["submit"] = "submit"


AnnotationAction = Annotated[
    WriteFileAction | PatchFileAction | CompileAction | SubmitAction,
    Field(discriminator="type"),
]


class AnnotationEditResponse(BaseModel):
    action: AnnotationAction
    notes: list[str] = Field(default_factory=list)


class ProviderEvent(BaseModel):
    type: Literal["message_delta", "tool_call", "completed", "error"]
    payload: dict[str, Any] = Field(default_factory=dict)


class ResearchSubtaskRequest(BaseModel):
    task_id: str
    node_id: str
    goal: str
    scope: str | None = None
    node_text: str
    reading_mode: str
    system_prompt: str


class ResearchSubtaskResponse(BaseModel):
    findings: list[ResearchFinding] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
