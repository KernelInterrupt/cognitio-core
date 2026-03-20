from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.domain.annotation import CompileError
from app.sandbox.templates import DEFAULT_TEX_TEMPLATE


@dataclass
class AnnotationWorkspace:
    workspace_id: str
    root: Path

    @property
    def file_path(self) -> Path:
        return self.root / "file.tex"

    def initialize(self, target_node_id: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            DEFAULT_TEX_TEMPLATE.format(target_node_id=target_node_id),
            encoding="utf-8",
        )

    def read_file(self) -> str:
        return self.file_path.read_text(encoding="utf-8")

    def read_editable_region(self) -> str:
        content = self.read_file()
        _, editable, _ = self._split_regions(content)
        return editable

    def write_editable_region(self, content: str) -> None:
        current = self.read_file()
        prefix, _, suffix = self._split_regions(current)
        rendered = f"{prefix}{content.rstrip()}\n{suffix}"
        self.file_path.write_text(rendered, encoding="utf-8")

    def replace_editable_region(self, old: str, new: str) -> None:
        editable = self.read_editable_region()
        if old in editable:
            updated = editable.replace(old, new, 1)
        else:
            updated = f"{editable.rstrip()}\n{new}"
        self.write_editable_region(updated)

    def validate_locked_regions(self) -> list[CompileError]:
        content = self.read_file()
        errors: list[CompileError] = []
        if "\\usepackage" not in content:
            errors.append(
                CompileError(
                    line=1,
                    message="Locked preamble was modified: missing \\usepackage block.",
                    code="LOCKED_REGION_MODIFICATION",
                )
            )
        if "\\documentclass" not in content or "\\end{document}" not in content:
            errors.append(
                CompileError(
                    line=1,
                    message="Locked document structure was modified.",
                    code="LOCKED_REGION_MODIFICATION",
                )
            )
        return errors

    @staticmethod
    def _split_regions(content: str) -> tuple[str, str, str]:
        editable_start = "% === EDITABLE START ===\n"
        editable_end = "\n% === EDITABLE END ==="
        start_index = content.index(editable_start) + len(editable_start)
        end_index = content.index(editable_end)
        prefix = content[:start_index]
        editable = content[start_index:end_index]
        suffix = content[end_index:]
        return prefix, editable, suffix
