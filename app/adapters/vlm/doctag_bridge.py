from __future__ import annotations

import re
from collections.abc import Iterable

from app.domain.vlm_page_analysis import VlmPageAnalysis, VlmPageBlock, VlmPageWarning

_TAG_PATTERN = re.compile(r"<(?P<tag>[a-zA-Z_]+)>(?P<body>.*?)</(?P=tag)>", re.DOTALL)
_LOC_PATTERN = re.compile(r"<loc_(\d+)>")
_ANY_TAG_PATTERN = re.compile(r"</?[a-zA-Z_]+>|<loc_\d+>")
_INSTRUCTION_PATTERN = re.compile(
    r"ignore previous|follow hidden|reviewer only|system prompt|secret instruction|jailbreak",
    re.IGNORECASE,
)

_KIND_MAP = {
    "picture": "figure",
    "figure": "figure",
    "table": "table",
    "equation": "equation",
    "formula": "equation",
    "code": "code",
    "title": "heading",
    "heading": "heading",
    "section_header": "heading",
    "text": "paragraph",
    "paragraph": "paragraph",
}


def parse_granite_doctag_to_page_analysis(
    content: str,
    *,
    page_no: int,
    text_layer: str | None = None,
) -> VlmPageAnalysis | None:
    if "<doctag>" not in content and "<loc_" not in content:
        return None

    text_blocks = _text_layer_blocks(text_layer or "")
    figure_like_blocks = _parse_tag_blocks(
        content,
        default_layer="supporting" if text_blocks else "primary",
    )

    blocks: list[VlmPageBlock] = []
    order = 1
    for block in text_blocks:
        block.reading_order = order
        blocks.append(block)
        order += 1
    for block in figure_like_blocks:
        block.reading_order = order
        blocks.append(block)
        order += 1

    visible_text = _visible_text(content)
    notes = ["granite_doctag_bridge_used"]
    if text_layer and not visible_text:
        notes.append("text_layer_fallback_used")
    if figure_like_blocks:
        notes.append(f"doctag_structural_blocks={len(figure_like_blocks)}")

    warnings = _detect_warnings(_join_evidence([text_layer or "", visible_text]))
    return VlmPageAnalysis(
        page_no=page_no,
        summary=_summarize_page(text_layer or visible_text),
        dominant_page_type=_infer_page_type(text_layer or visible_text),
        blocks=blocks,
        warnings=warnings,
        notes=notes,
    )


def _parse_tag_blocks(
    content: str,
    *,
    default_layer: str = "primary",
) -> list[VlmPageBlock]:
    inner = content.replace("<doctag>", "").replace("</doctag>", "")
    seen: set[tuple[str, tuple[float, float, float, float] | None, str]] = set()
    blocks: list[VlmPageBlock] = []
    for match in _TAG_PATTERN.finditer(inner):
        tag = match.group("tag").lower()
        body = match.group("body")
        kind = _KIND_MAP.get(tag, "unknown")
        bbox = _bbox_from_text(body)
        text = _visible_text(body)
        if kind == "unknown" and not text:
            continue
        if kind in {"figure", "table", "equation"} and not text:
            text = f"[{kind}]"
        key = (kind, bbox, text)
        if key in seen:
            continue
        seen.add(key)
        blocks.append(
            VlmPageBlock(
                kind=kind,
                layer=default_layer,
                text=text,
                bbox=bbox,
                reading_order=0,
                rationale="derived_from_doctag",
            )
        )
    return blocks


def _bbox_from_text(text: str) -> tuple[float, float, float, float] | None:
    vals = [float(item) for item in _LOC_PATTERN.findall(text)]
    if len(vals) < 4:
        return None
    return (vals[0], vals[1], vals[2], vals[3])


def _visible_text(text: str) -> str:
    stripped = _ANY_TAG_PATTERN.sub(" ", text)
    return re.sub(r"\s+", " ", stripped).strip()


def _text_layer_blocks(text_layer: str) -> list[VlmPageBlock]:
    text = text_layer.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    if re.search(r"(^|\n)Abstract(\n|$)", text, re.IGNORECASE):
        return _title_page_blocks(text)

    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    blocks: list[VlmPageBlock] = []
    for chunk in chunks:
        blocks.append(
            VlmPageBlock(
                kind=_guess_chunk_kind(chunk),
                layer="primary",
                text=chunk,
                reading_order=0,
                rationale="derived_from_text_layer",
            )
        )
    return blocks

def _title_page_blocks(text: str) -> list[VlmPageBlock]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    blocks: list[VlmPageBlock] = []
    index = 0

    notice_lines: list[str] = []
    while index < len(lines):
        line = lines[index]
        if line.lower() == "abstract" or _is_affiliation_line(line):
            break
        if notice_lines and _looks_like_title(line) and not _looks_like_notice(line):
            break
        if _looks_like_notice(line):
            notice_lines.append(line)
            index += 1
            continue
        if notice_lines and not _looks_like_notice(line):
            notice_lines.append(line)
            index += 1
            continue
        break
    if notice_lines:
        blocks.append(
            VlmPageBlock(
                kind="paragraph",
                layer="primary",
                text=" ".join(notice_lines),
                reading_order=0,
                rationale="title_page_notice",
            )
        )

    title_lines: list[str] = []
    while index < len(lines):
        line = lines[index]
        lower = line.lower()
        if lower == "abstract" or "@" in line or _is_affiliation_line(line):
            break
        if title_lines and _looks_like_author_name(line):
            break
        if title_lines or _looks_like_title(line):
            title_lines.append(line)
            index += 1
            continue
        break
    if title_lines:
        blocks.append(
            VlmPageBlock(
                kind="heading",
                layer="primary",
                text=" ".join(title_lines),
                reading_order=0,
                rationale="title_page_title",
            )
        )

    meta_lines: list[str] = []
    while index < len(lines):
        line = lines[index]
        if line.lower() == "abstract":
            break
        meta_lines.append(line)
        index += 1
    if meta_lines:
        blocks.append(
            VlmPageBlock(
                kind="paragraph",
                layer="primary",
                text="\n".join(meta_lines),
                reading_order=0,
                rationale="title_page_authors_and_affiliations",
            )
        )

    if index < len(lines) and lines[index].lower() == "abstract":
        blocks.append(
            VlmPageBlock(
                kind="heading",
                layer="primary",
                text="Abstract",
                reading_order=0,
                rationale="abstract_heading",
            )
        )
        index += 1

    abstract_lines: list[str] = []
    while index < len(lines):
        line = lines[index]
        if _looks_like_footer(line):
            break
        abstract_lines.append(line)
        index += 1
    if abstract_lines:
        blocks.append(
            VlmPageBlock(
                kind="paragraph",
                layer="primary",
                text=" ".join(abstract_lines),
                reading_order=0,
                rationale="abstract_body",
            )
        )

    footer_lines = [line for line in lines[index:] if line]
    if footer_lines:
        blocks.append(
            VlmPageBlock(
                kind="paragraph",
                layer="primary",
                text="\n".join(footer_lines),
                reading_order=0,
                rationale="title_page_footer",
            )
        )

    return blocks


def _guess_chunk_kind(chunk: str) -> str:
    lower = chunk.lower()
    if lower.startswith("figure ") or lower.startswith("fig. "):
        return "figure"
    if lower.startswith("table "):
        return "table"
    if _looks_like_title(chunk):
        return "heading"
    return "paragraph"


def _looks_like_title(line: str) -> bool:
    words = line.split()
    if not words or len(words) > 16:
        return False
    if line.endswith("."):
        return False
    if any(ch.isdigit() for ch in line):
        return False
    alpha_count = sum(1 for ch in line if ch.isalpha())
    uppercase_ratio = sum(1 for ch in line if ch.isupper()) / max(1, alpha_count)
    return uppercase_ratio > 0.15 or line.istitle()


def _is_affiliation_line(line: str) -> bool:
    lower = line.lower()
    if _looks_like_notice(line):
        return False
    keywords = ("university", "google", "brain", "research", "@", "institute", "department")
    return any(keyword in lower for keyword in keywords)


def _looks_like_author_name(line: str) -> bool:
    cleaned = re.sub(r"[^A-Za-zÀ-ÿ\s.-]", "", line).strip()
    words = [word for word in cleaned.split() if word]
    if not 2 <= len(words) <= 4:
        return False
    if any(word.lower() in {"attention", "abstract", "provided"} for word in words):
        return False
    return all(word[:1].isupper() for word in words if word[:1].isalpha())


def _looks_like_notice(line: str) -> bool:
    lower = line.lower()
    return any(
        token in lower
        for token in ("permission", "attribution", "journalistic", "scholarly")
    )


def _looks_like_footer(line: str) -> bool:
    lower = line.lower()
    return (
        lower.startswith("*")
        or lower.startswith("†")
        or lower.startswith("‡")
        or "conference" in lower
    )


def _infer_page_type(text: str) -> str:
    lower = text.lower()
    if not lower.strip():
        return "unknown"
    if "abstract" in lower and (
        lower.count("@") >= 2 or "google" in lower or "university" in lower
    ):
        return "title_page"
    if lower.count("figure") + lower.count("fig.") >= 3:
        return "figure_heavy"
    if lower.count("table") >= 3:
        return "table_heavy"
    if len(re.findall(r"(^|\n)\s*(step\s+\d+|\d+[.)])", text, re.IGNORECASE)) >= 3:
        return "manual_step_page"
    return "paper_body"


def _summarize_page(text: str) -> str | None:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return None
    return compact[:220]


def _detect_warnings(text: str) -> list[VlmPageWarning]:
    if not text:
        return []
    matches = [match.group(0) for match in _INSTRUCTION_PATTERN.finditer(text)]
    if not matches:
        return []
    evidence = list(dict.fromkeys(matches))
    return [
        VlmPageWarning(
            kind="instruction_like_content",
            severity="high",
            message=(
                "The page appears to contain instruction-like content "
                "that may be targeting the model."
            ),
            evidence=evidence,
        )
    ]


def _join_evidence(parts: Iterable[str]) -> str:
    return "\n".join(part for part in parts if part)
