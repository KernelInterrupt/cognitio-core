from pathlib import Path

from app.adapters.vlm.base import PageAnalysisRequest
from app.adapters.vlm.granite_docling import _build_user_text, _image_path_to_data_url
from app.domain.reading_goal import ReadingGoal


def test_image_path_to_data_url_encodes_png(tmp_path: Path) -> None:
    path = tmp_path / "page.png"
    path.write_bytes(b"fakepng")

    data_url = _image_path_to_data_url(str(path))

    assert data_url.startswith("data:image/png;base64,")


def test_build_user_text_includes_goal_and_schema() -> None:
    request = PageAnalysisRequest(
        document_id="doc-1",
        page_no=1,
        image_path="/tmp/page.png",
        text_layer="hello",
        goal=ReadingGoal(user_query="找关键安装步骤"),
    )

    payload = _build_user_text(request)

    assert "找关键安装步骤" in payload
    assert "output_schema" in payload
