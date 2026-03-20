from __future__ import annotations

from app.domain.annotation import CompileError, CompileResult
from app.sandbox.templates import EDITABLE_END, EDITABLE_START, LOCKED_END, LOCKED_START


class FakeCompiler:
    def compile(self, content: str) -> CompileResult:
        required_markers = [LOCKED_START, LOCKED_END, EDITABLE_START, EDITABLE_END]
        missing = [marker for marker in required_markers if marker not in content]
        if missing:
            return CompileResult(
                ok=False,
                errors=[
                    CompileError(
                        line=1,
                        message=f"Missing required locked/editable markers: {', '.join(missing)}",
                        code="LOCKED_REGION_MODIFICATION",
                    )
                ],
            )
        if "\\annotationtype{" not in content:
            return CompileResult(
                ok=False,
                errors=[
                    CompileError(
                        line=1,
                        message="Missing \\annotationtype declaration",
                        code="COMPILE_VALIDATION_ERROR",
                    )
                ],
            )
        if "\\target{" not in content:
            return CompileResult(
                ok=False,
                errors=[
                    CompileError(
                        line=1,
                        message="Missing \\target declaration",
                        code="COMPILE_VALIDATION_ERROR",
                    )
                ],
            )
        body = content.strip().splitlines()
        rendered = "\n".join(
            line
            for line in body
            if not line.startswith("\\")
            and line not in {LOCKED_START, LOCKED_END, EDITABLE_START, EDITABLE_END}
        ).strip()
        return CompileResult(ok=True, rendered_content=rendered or "")
