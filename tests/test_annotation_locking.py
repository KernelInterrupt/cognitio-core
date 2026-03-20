from pathlib import Path

from app.sandbox.compiler import FakeCompiler
from app.sandbox.handle import WorkspaceHandle
from app.sandbox.workspace import AnnotationWorkspace


def test_workspace_only_writes_editable_region(tmp_path: Path) -> None:
    workspace = AnnotationWorkspace(workspace_id="ws_1", root=tmp_path / "ws_1")
    workspace.initialize("p_1")

    original = workspace.read_file()
    workspace.write_editable_region("新的批注内容。")
    updated = workspace.read_file()

    assert "\\usepackage{amsmath}" in updated
    assert "\\documentclass{article}" in updated
    assert "新的批注内容。" in updated
    original_prefix = original.split("% === EDITABLE START ===")[0]
    updated_prefix = updated.split("% === EDITABLE START ===")[0]
    assert original_prefix == updated_prefix


def test_compiler_rejects_missing_locked_markers() -> None:
    result = FakeCompiler().compile("这里只有正文，没有锁定标记。")
    assert not result.ok
    assert result.errors[0].code == "LOCKED_REGION_MODIFICATION"


def test_workspace_handle_playwright_like_api(tmp_path: Path) -> None:
    workspace = AnnotationWorkspace(workspace_id="ws_2", root=tmp_path / "ws_2")
    workspace.initialize("p_2")
    handle = WorkspaceHandle(workspace=workspace, compiler=FakeCompiler())

    assert "这里写批注内容" in handle.read_body()
    handle.write_body("第一版批注。")
    assert "第一版批注。" in handle.read_file()

    handle.patch_body("第一版批注。", "第二版批注。")
    result = handle.compile_annotation()

    assert result.ok
    assert result.rendered_content == "第二版批注。"
    assert handle.get_compile_errors() == []
    assert handle.submit_annotation() == "第二版批注。"
    assert handle.submitted
