from __future__ import annotations

from pathlib import Path

from app.adapters.llm.base import ModelProvider
from app.adapters.llm.models import AnnotationEditRequest
from app.domain.annotation import Annotation, CompileResult
from app.prompts.loader import load_prompt
from app.sandbox.compiler import FakeCompiler
from app.sandbox.handle import WorkspaceHandle
from app.sandbox.workspace import AnnotationWorkspace


class AnnotationService:
    def __init__(
        self,
        provider: ModelProvider,
        workspace_root: Path | None = None,
        compiler: FakeCompiler | None = None,
    ) -> None:
        self.provider = provider
        self.workspace_root = workspace_root or Path(".cognitio/workspaces")
        self.compiler = compiler or FakeCompiler()

    async def render_annotation(
        self,
        annotation: Annotation,
        max_attempts: int = 2,
    ) -> tuple[WorkspaceHandle, CompileResult]:
        workspace = AnnotationWorkspace(
            workspace_id=f"ws_{annotation.annotation_id}",
            root=self.workspace_root / annotation.annotation_id,
        )
        workspace.initialize(annotation.target_node_id)
        handle = WorkspaceHandle(workspace=workspace, compiler=self.compiler)

        compile_errors = []
        result = CompileResult(ok=False)
        prompt = load_prompt("annotation_system.md")

        for _ in range(max_attempts):
            response = await self.provider.edit_annotation(
                AnnotationEditRequest(
                    annotation_id=annotation.annotation_id,
                    target_node_id=annotation.target_node_id,
                    annotation_type=annotation.type,
                    language=annotation.language,
                    current_file=handle.read_file(),
                    editable_region=handle.read_body(),
                    compile_errors=compile_errors,
                    system_prompt=prompt,
                )
            )

            action = response.action
            if action.type == "write_file":
                handle.write_body(action.content)
            elif action.type == "patch_file":
                handle.patch_body(action.old, action.new)

            result = handle.compile_annotation()
            if result.ok:
                handle.submit_annotation()
                return handle, result

            compile_errors = result.errors

        return handle, result
