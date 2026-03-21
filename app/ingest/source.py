from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class DocumentSource(BaseModel):
    text: str | None = None
    uri: str | None = None
    path: str | None = None
    filename: str | None = None
    media_type: str | None = None
    content_bytes: bytes | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_text(
        cls,
        text: str,
        *,
        filename: str | None = None,
        media_type: str = "text/plain",
    ) -> DocumentSource:
        return cls(text=text, filename=filename, media_type=media_type)

    @classmethod
    def from_path(cls, path: str | Path, media_type: str | None = None) -> DocumentSource:
        path_obj = Path(path)
        guessed = media_type or _guess_media_type(path_obj)
        text = None
        if guessed.startswith("text/") or guessed == "application/x-latex":
            text = path_obj.read_text(encoding="utf-8")
        return cls(
            path=str(path_obj),
            uri=path_obj.resolve().as_uri(),
            filename=path_obj.name,
            media_type=guessed,
            text=text,
        )


_DEF_MEDIA_BY_SUFFIX = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".tex": "application/x-latex",
}


def _guess_media_type(path: Path) -> str:
    return _DEF_MEDIA_BY_SUFFIX.get(path.suffix.lower(), "application/octet-stream")
