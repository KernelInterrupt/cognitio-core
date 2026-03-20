from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.annotation import CompileResult
from app.sandbox.compiler import FakeCompiler
from app.sandbox.workspace import AnnotationWorkspace


@dataclass
class WorkspaceHandle:
    workspace: AnnotationWorkspace
    compiler: FakeCompiler
    last_compile_result: CompileResult | None = field(default=None, init=False)
    submitted: bool = field(default=False, init=False)

    @property
    def workspace_id(self) -> str:
        return self.workspace.workspace_id

    def read_file(self) -> str:
        return self.workspace.read_file()

    def read_body(self) -> str:
        return self.workspace.read_editable_region()

    def write_body(self, content: str) -> None:
        self.workspace.write_editable_region(content)

    def patch_body(self, old: str, new: str) -> None:
        self.workspace.replace_editable_region(old, new)

    def compile_annotation(self) -> CompileResult:
        locked_errors = self.workspace.validate_locked_regions()
        if locked_errors:
            self.last_compile_result = CompileResult(ok=False, errors=locked_errors)
        else:
            self.last_compile_result = self.compiler.compile(self.workspace.read_file())
        return self.last_compile_result

    def get_compile_errors(self) -> list[dict[str, str | int | None]]:
        if self.last_compile_result is None:
            return []
        return [error.model_dump(mode="json") for error in self.last_compile_result.errors]

    def submit_annotation(self) -> str:
        if self.last_compile_result is None or not self.last_compile_result.ok:
            raise RuntimeError("Cannot submit annotation before a successful compile.")
        self.submitted = True
        return self.last_compile_result.rendered_content or ""
