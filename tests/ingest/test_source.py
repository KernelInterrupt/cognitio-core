from pathlib import Path

from app.ingest.source import DocumentSource


def test_document_source_from_path_reads_text(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("hello", encoding="utf-8")

    source = DocumentSource.from_path(path)

    assert source.media_type == "text/plain"
    assert source.text == "hello"
    assert source.filename == "sample.txt"
