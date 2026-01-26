"""Markdown to PDF rendering helpers for chatroom analysis reports."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import httpx
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    import regex as regex_module
except ImportError:
    regex_module = None

_TABLE_SEPARATOR_RE = re.compile(r"^[\s|:-]+$")
_NUMBERED_ITEM_RE = re.compile(r"^(\d+)\.\s+(.*)$")
_EMOJI_RE = re.compile(
    r"([\U0001F1E6-\U0001F1FF]{2}|"
    r"[\U0001F300-\U0001F5FF"
    r"\U0001F600-\U0001F64F"
    r"\U0001F680-\U0001F6FF"
    r"\U0001F700-\U0001F77F"
    r"\U0001F780-\U0001F7FF"
    r"\U0001F800-\U0001F8FF"
    r"\U0001F900-\U0001F9FF"
    r"\U0001FA00-\U0001FAFF"
    r"\U00002700-\U000027BF"
    r"\U00002600-\U000026FF"
    r"\u2600-\u26FF"
    r"\u2700-\u27BF"
    r"]"
    r"(?:\uFE0F|\u200D"
    r"[\U0001F300-\U0001FAFF"
    r"\U00002700-\U000027BF"
    r"\U00002600-\U000026FF"
    r"])*"
    r"(?:[\U0001F3FB-\U0001F3FF])?)"
)
_GRAPHEME_RE = regex_module.compile(r"\X") if regex_module else None
_EMOJI_LIKE_RE = (
    regex_module.compile(r"(\p{Extended_Pictographic}|\p{Emoji_Presentation})")
    if regex_module
    else None
)
_DEFAULT_TWEMOJI_BASE_URL = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72"
_EMOJI_PNG_CACHE: dict[tuple[Path, str], Path | None] = {}


@dataclass(frozen=True)
class PdfRenderOptions:
    page_width: int = 420
    page_height: int = 840
    margin_left: int = 28
    margin_right: int = 28
    margin_top: int = 36
    margin_bottom: int = 36
    base_font_size: int = 20
    line_height: float = 1.6
    table_font_size: int = 14
    emoji_image_scale: float = 0.8
    emoji_image_valign: str = "middle"
    emoji_auto_download: bool = True
    emoji_base_url: str = _DEFAULT_TWEMOJI_BASE_URL


def render_markdown_report_pdf(
    markdown_path: Path,
    output_path: Path,
    font_path: Path | None = None,
    font_index: int | None = None,
    emoji_image_dir: Path | None = None,
    options: PdfRenderOptions | None = None,
) -> None:
    markdown_text = markdown_path.read_text(encoding="utf-8")
    render_markdown_pdf(
        markdown_text=markdown_text,
        output_path=output_path,
        font_path=font_path,
        font_index=font_index,
        emoji_image_dir=emoji_image_dir,
        options=options,
    )


def render_markdown_pdf(
    markdown_text: str,
    output_path: Path,
    font_path: Path | None = None,
    font_index: int | None = None,
    emoji_image_dir: Path | None = None,
    options: PdfRenderOptions | None = None,
) -> None:
    render_options = options or PdfRenderOptions()
    resolved_font_path = _resolve_source_han_sans(font_path)
    font_name = _register_font(resolved_font_path, font_name="SourceHanSans", font_index=font_index)
    bold_font_name = font_name
    resolved_bold_path = _resolve_source_han_sans_bold(resolved_font_path)
    if resolved_bold_path:
        bold_font_name = _register_font(
            resolved_bold_path,
            font_name="SourceHanSans-Bold",
            font_index=font_index,
        )
    auto_download = _emoji_auto_download_enabled(render_options.emoji_auto_download)
    resolved_emoji_image_dir = _resolve_emoji_image_dir(
        emoji_image_dir, auto_download=auto_download
    )
    emoji_base_url = _resolve_emoji_base_url(render_options.emoji_base_url)
    styles = _build_styles(font_name, bold_font_name, render_options)
    flowables = _build_flowables(
        markdown_text,
        styles,
        render_options,
        emoji_image_dir=resolved_emoji_image_dir,
        emoji_auto_download=auto_download,
        emoji_base_url=emoji_base_url,
        bold_font_name=bold_font_name,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=(render_options.page_width, render_options.page_height),
        leftMargin=render_options.margin_left,
        rightMargin=render_options.margin_right,
        topMargin=render_options.margin_top,
        bottomMargin=render_options.margin_bottom,
    )
    doc.build(flowables)


def _resolve_source_han_sans(font_path: Path | None) -> Path:
    if font_path:
        if font_path.exists():
            return font_path
        raise FileNotFoundError(f"指定字体文件不存在: {font_path}")

    env_path = os.environ.get("SOURCE_HAN_SANS_PATH")
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists():
            return candidate

    candidates = [
        "SourceHanSansSC-Regular.ttc",
        "SourceHanSansCN-Regular.ttc",
        "SourceHanSans-Regular.ttc",
        "SourceHanSansSC-Regular.ttf",
        "SourceHanSansCN-Regular.ttf",
        "SourceHanSans-Regular.ttf",
        "SourceHanSansSC-Regular.otf",
        "SourceHanSansCN-Regular.otf",
        "SourceHanSans-Regular.otf",
    ]
    search_dirs = _font_search_dirs()
    for directory in search_dirs:
        for name in candidates:
            candidate = directory / name
            if candidate.exists():
                return candidate
        for glob in ("SourceHanSans*.ttc", "SourceHanSans*.ttf", "SourceHanSans*.otf"):
            matches = list(directory.glob(glob))
            if matches:
                return matches[0]

    searched = ", ".join(str(path) for path in search_dirs)
    raise FileNotFoundError(
        "未找到思源黑体字体文件，请下载 Source Han Sans 并放到以下目录之一: "
        f"{searched}. 也可以通过 --font-path 或 SOURCE_HAN_SANS_PATH 指定字体路径。"
    )


def _resolve_source_han_sans_bold(regular_path: Path) -> Path | None:
    env_path = os.environ.get("SOURCE_HAN_SANS_BOLD_PATH")
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists():
            return candidate

    candidates = [
        "SourceHanSansSC-Bold.ttc",
        "SourceHanSansCN-Bold.ttc",
        "SourceHanSans-Bold.ttc",
        "SourceHanSansSC-Bold.ttf",
        "SourceHanSansCN-Bold.ttf",
        "SourceHanSans-Bold.ttf",
    ]
    search_dirs = [regular_path.parent] + _font_search_dirs()
    for directory in search_dirs:
        for name in candidates:
            candidate = directory / name
            if candidate.exists():
                return candidate
        for glob in ("SourceHanSans*Bold*.ttc", "SourceHanSans*Bold*.ttf"):
            matches = list(directory.glob(glob))
            if matches:
                return matches[0]

    return None


def _resolve_emoji_image_dir(emoji_dir: Path | None, auto_download: bool) -> Path | None:
    if emoji_dir:
        if emoji_dir.exists():
            return emoji_dir
        raise FileNotFoundError(f"指定 emoji 图片目录不存在: {emoji_dir}")

    env_path = os.environ.get("TWEMOJI_DIR") or os.environ.get("EMOJI_IMAGE_DIR")
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists():
            return candidate
        if auto_download:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate

    project_root = Path(__file__).resolve().parents[3]
    candidates = [
        project_root / "assets" / "twemoji" / "72x72",
        project_root / "assets" / "twemoji",
        project_root / "data" / "twemoji" / "72x72",
        project_root / "data" / "twemoji",
        project_root / "assets" / "emoji",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    if auto_download:
        cache_dir = project_root / "data" / "twemoji" / "72x72"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    return None


def _emoji_auto_download_enabled(default_enabled: bool) -> bool:
    env_value = os.environ.get("EMOJI_AUTO_DOWNLOAD")
    if env_value is None:
        return default_enabled
    return env_value.strip().lower() not in {"0", "false", "no", "off"}


def _resolve_emoji_base_url(base_url: str) -> str:
    env_value = os.environ.get("TWEMOJI_BASE_URL")
    if env_value:
        return env_value.strip().rstrip("/")
    return base_url.rstrip("/")


def _font_search_dirs() -> list[Path]:
    project_root = Path(__file__).resolve().parents[3]
    home = Path.home()
    return [
        project_root / "assets" / "fonts",
        project_root / "data" / "fonts",
        project_root / "fonts",
        home / "Library" / "Fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        home / ".local" / "share" / "fonts",
        Path("/usr/share/fonts"),
        Path("C:/Windows/Fonts"),
    ]


def _register_font(font_path: Path, font_name: str, font_index: int | None = None) -> str:
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name

    suffix = font_path.suffix.lower()
    try:
        if suffix == ".ttc":
            subfont_index = 0 if font_index is None else font_index
            pdfmetrics.registerFont(TTFont(font_name, str(font_path), subfontIndex=subfont_index))
        else:
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    except TTFError as exc:
        message = str(exc)
        if "postscript outlines are not supported" in message:
            raise ValueError(
                "检测到 CFF 轮廓的 OTF 字体，ReportLab 不支持该格式。"
                "请改用 TrueType 轮廓的 TTF/TTC 版本的思源黑体，"
                "或使用 --font-path 指向可用的 TTF/TTC 字体。"
            ) from exc
        raise
    return font_name


def _build_styles(
    font_name: str, bold_font_name: str, options: PdfRenderOptions
) -> dict[str, ParagraphStyle]:
    base = options.base_font_size
    line_height = options.line_height
    return {
        "title": ParagraphStyle(
            name="Title",
            fontName=bold_font_name,
            fontSize=base + 8,
            leading=(base + 8) * line_height,
            spaceAfter=base * 0.6,
        ),
        "kicker": ParagraphStyle(
            name="Kicker",
            fontName=bold_font_name,
            fontSize=base - 1,
            leading=(base - 1) * line_height,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=base * 0.5,
        ),
        "section": ParagraphStyle(
            name="Section",
            fontName=bold_font_name,
            fontSize=base + 3,
            leading=(base + 3) * line_height,
            spaceBefore=base * 0.3,
            spaceAfter=base * 0.4,
        ),
        "subsection": ParagraphStyle(
            name="Subsection",
            fontName=font_name,
            fontSize=base + 2,
            leading=(base + 2) * line_height,
            spaceBefore=base * 0.2,
            spaceAfter=base * 0.3,
        ),
        "body": ParagraphStyle(
            name="Body",
            fontName=font_name,
            fontSize=base,
            leading=base * line_height,
            spaceAfter=base * 0.4,
        ),
        "meta": ParagraphStyle(
            name="Meta",
            fontName=font_name,
            fontSize=base - 2,
            leading=(base - 2) * line_height,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=base * 0.2,
        ),
        "meta_small": ParagraphStyle(
            name="MetaSmall",
            fontName=font_name,
            fontSize=base - 4,
            leading=(base - 4) * line_height,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=base * 0.2,
        ),
        "summary": ParagraphStyle(
            name="Summary",
            fontName=font_name,
            fontSize=base,
            leading=base * line_height,
            textColor=colors.HexColor("#111827"),
            spaceAfter=base * 0.6,
        ),
        "date": ParagraphStyle(
            name="Date",
            fontName=font_name,
            fontSize=base,
            leading=base * line_height,
            textColor=colors.HexColor("#2563EB"),
            spaceAfter=base * 0.4,
        ),
        "bullet": ParagraphStyle(
            name="Bullet",
            fontName=font_name,
            fontSize=base,
            leading=base * line_height,
            leftIndent=base * 0.8,
            bulletIndent=0,
            spaceAfter=base * 0.2,
        ),
        "numbered": ParagraphStyle(
            name="Numbered",
            fontName=font_name,
            fontSize=base,
            leading=base * line_height,
            leftIndent=base * 0.8,
            bulletIndent=0,
            spaceAfter=base * 0.25,
        ),
        "table_header": ParagraphStyle(
            name="TableHeader",
            fontName=font_name,
            fontSize=options.table_font_size,
            leading=options.table_font_size * 1.4,
        ),
        "table_cell": ParagraphStyle(
            name="TableCell",
            fontName=font_name,
            fontSize=options.table_font_size,
            leading=options.table_font_size * 1.4,
        ),
    }


def _build_flowables(
    markdown_text: str,
    styles: dict[str, ParagraphStyle],
    options: PdfRenderOptions,
    emoji_image_dir: Path | None = None,
    emoji_auto_download: bool = False,
    emoji_base_url: str | None = None,
    bold_font_name: str | None = None,
):
    flowables: list = []
    lines = markdown_text.splitlines()
    index = 0
    topic_count = 0

    def format_text(text: str, style: ParagraphStyle) -> str:
        return _format_paragraph_text(
            text,
            emoji_image_dir=emoji_image_dir,
            emoji_auto_download=emoji_auto_download,
            emoji_base_url=emoji_base_url,
            emoji_image_scale=options.emoji_image_scale,
            emoji_image_valign=options.emoji_image_valign,
            font_size=style.fontSize,
        )

    while index < len(lines):
        line = lines[index].rstrip()
        if not line.strip():
            index += 1
            continue

        if line.startswith("# "):
            flowables.append(
                Paragraph(
                    format_text(line[2:].strip(), styles["title"]),
                    styles["title"],
                )
            )
            index += 1
            continue
        if line.strip() == "热门话题 Top 10":
            flowables.append(
                Paragraph(format_text(line.strip(), styles["kicker"]), styles["kicker"])
            )
            index += 1
            continue
        if line.startswith("## "):
            if topic_count > 0:
                flowables.append(
                    HRFlowable(
                        width="100%",
                        thickness=0.5,
                        color=colors.HexColor("#E5E7EB"),
                        spaceBefore=options.base_font_size * 0.6,
                        spaceAfter=options.base_font_size * 0.6,
                    )
                )
            topic_count += 1
            flowables.append(
                Paragraph(
                    format_text(line[3:].strip(), styles["section"]),
                    styles["section"],
                )
            )
            index += 1
            continue
        if line.startswith("### "):
            flowables.append(
                Paragraph(
                    format_text(line[4:].strip(), styles["subsection"]),
                    styles["subsection"],
                )
            )
            index += 1
            continue

        if _is_table_line(line):
            table_lines, index = _consume_table(lines, index)
            table = _build_table(
                table_lines,
                styles,
                options,
                emoji_image_dir=emoji_image_dir,
                emoji_auto_download=emoji_auto_download,
                emoji_base_url=emoji_base_url,
            )
            flowables.append(table)
            flowables.append(Spacer(1, options.base_font_size * 0.6))
            continue

        if line.startswith("- "):
            if line.startswith("- 日期:"):
                flowables.append(
                    Paragraph(
                        format_text(line[2:].strip(), styles["date"]),
                        styles["date"],
                    )
                )
                index += 1
                continue
            flowables.append(
                Paragraph(
                    format_text(line[2:].strip(), styles["bullet"]),
                    styles["bullet"],
                    bulletText="-",
                )
            )
            index += 1
            continue

        numbered_match = _NUMBERED_ITEM_RE.match(line)
        if numbered_match:
            flowables.append(
                Paragraph(
                    format_text(numbered_match.group(2).strip(), styles["numbered"]),
                    styles["numbered"],
                    bulletText=f"{numbered_match.group(1)}.",
                )
            )
            index += 1
            continue

        stripped = line.strip()
        if stripped.startswith("分类:"):
            label, value = _split_label_value(stripped)
            flowables.append(
                Paragraph(
                    _format_labeled_line(
                        label,
                        value,
                        bold_font_name=bold_font_name,
                        emoji_image_dir=emoji_image_dir,
                        emoji_auto_download=emoji_auto_download,
                        emoji_base_url=emoji_base_url,
                        emoji_image_scale=options.emoji_image_scale,
                        emoji_image_valign=options.emoji_image_valign,
                        font_size=styles["meta"].fontSize,
                    ),
                    styles["meta"],
                )
            )
            index += 1
            continue
        if stripped.startswith("时间范围:"):
            label, value = _split_label_value(stripped)
            flowables.append(
                Paragraph(
                    _format_labeled_line(
                        label,
                        value,
                        bold_font_name=bold_font_name,
                        emoji_image_dir=emoji_image_dir,
                        emoji_auto_download=emoji_auto_download,
                        emoji_base_url=emoji_base_url,
                        emoji_image_scale=options.emoji_image_scale,
                        emoji_image_valign=options.emoji_image_valign,
                        font_size=styles["meta"].fontSize,
                    ),
                    styles["meta"],
                )
            )
            index += 1
            continue
        if stripped.startswith("热门度/消息数/参与人数:"):
            label, value = _split_label_value(stripped)
            flowables.append(
                Paragraph(
                    _format_labeled_line(
                        label,
                        value,
                        bold_font_name=bold_font_name,
                        emoji_image_dir=emoji_image_dir,
                        emoji_auto_download=emoji_auto_download,
                        emoji_base_url=emoji_base_url,
                        emoji_image_scale=options.emoji_image_scale,
                        emoji_image_valign=options.emoji_image_valign,
                        font_size=styles["meta_small"].fontSize,
                    ),
                    styles["meta_small"],
                )
            )
            index += 1
            continue
        if stripped.startswith("话题摘要:"):
            label, value = _split_label_value(stripped)
            flowables.append(
                Paragraph(
                    _format_labeled_line(
                        label,
                        value,
                        bold_font_name=bold_font_name,
                        emoji_image_dir=emoji_image_dir,
                        emoji_auto_download=emoji_auto_download,
                        emoji_base_url=emoji_base_url,
                        emoji_image_scale=options.emoji_image_scale,
                        emoji_image_valign=options.emoji_image_valign,
                        font_size=styles["summary"].fontSize,
                    ),
                    styles["summary"],
                )
            )
            index += 1
            continue
        flowables.append(Paragraph(format_text(stripped, styles["body"]), styles["body"]))
        index += 1

    return flowables


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and "|" in stripped[1:]


def _consume_table(lines: list[str], start_index: int) -> tuple[list[str], int]:
    table_lines: list[str] = []
    index = start_index
    while index < len(lines) and _is_table_line(lines[index]):
        table_lines.append(lines[index])
        index += 1
    return table_lines, index


def _build_table(
    table_lines: Iterable[str],
    styles: dict[str, ParagraphStyle],
    options: PdfRenderOptions,
    emoji_image_dir: Path | None,
    emoji_auto_download: bool = False,
    emoji_base_url: str | None = None,
) -> Table:
    rows = [_split_table_row(line) for line in table_lines]
    if not rows:
        return Table([[]])

    header = rows[0]
    data_rows = rows[1:]
    if data_rows and _TABLE_SEPARATOR_RE.match("".join(data_rows[0])):
        data_rows = data_rows[1:]

    normalized = [header]
    for row in data_rows:
        normalized.append(_normalize_row(row, len(header)))

    table_data = []
    for row_index, row in enumerate(normalized):
        style_key = "table_header" if row_index == 0 else "table_cell"
        style = styles[style_key]
        table_data.append(
            [
                Paragraph(
                    _format_paragraph_text(
                        cell,
                        emoji_image_dir=emoji_image_dir,
                        emoji_auto_download=emoji_auto_download,
                        emoji_base_url=emoji_base_url,
                        emoji_image_scale=options.emoji_image_scale,
                        emoji_image_valign=options.emoji_image_valign,
                        font_size=style.fontSize,
                    ),
                    style,
                )
                for cell in row
            ]
        )

    content_width = options.page_width - options.margin_left - options.margin_right
    col_widths = _table_col_widths(content_width, len(header))
    table = Table(table_data, colWidths=col_widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _split_table_row(line: str) -> list[str]:
    return [segment.strip() for segment in line.strip().strip("|").split("|")]


def _normalize_row(row: list[str], target_len: int) -> list[str]:
    if len(row) < target_len:
        return row + [""] * (target_len - len(row))
    if len(row) > target_len:
        return row[:target_len]
    return row


def _table_col_widths(content_width: int, columns: int) -> list[float]:
    if columns == 7:
        ratios = [0.06, 0.36, 0.1, 0.12, 0.12, 0.12, 0.12]
    elif columns == 4:
        ratios = [0.1, 0.5, 0.2, 0.2]
    else:
        ratios = [1 / columns] * columns
    return [content_width * ratio for ratio in ratios]


def _format_paragraph_text(
    text: str,
    emoji_image_dir: Path | None,
    emoji_auto_download: bool,
    emoji_base_url: str | None,
    emoji_image_scale: float,
    emoji_image_valign: str,
    font_size: float,
) -> str:
    if not emoji_image_dir:
        return escape(text)

    parts: list[str] = []
    for grapheme in _split_graphemes(text):
        if _looks_like_emoji(grapheme):
            png_path = _resolve_emoji_png(
                grapheme,
                emoji_image_dir,
                emoji_auto_download=emoji_auto_download,
                emoji_base_url=emoji_base_url,
            )
            if png_path:
                size = font_size * emoji_image_scale
                parts.append(_format_emoji_image_tag(png_path, size, emoji_image_valign))
                continue
        parts.append(escape(grapheme))

    return "".join(parts)


def _split_graphemes(text: str) -> list[str]:
    if _GRAPHEME_RE:
        return [str(part) for part in _GRAPHEME_RE.findall(text)]
    return list(text)


def _looks_like_emoji(grapheme: str) -> bool:
    if _EMOJI_LIKE_RE:
        return bool(_EMOJI_LIKE_RE.search(grapheme))
    return bool(_EMOJI_RE.search(grapheme))


def _twemoji_filename_candidates(grapheme: str) -> list[str]:
    codepoints = [ord(ch) for ch in grapheme]
    hexes = [f"{cp:x}" for cp in codepoints]
    keep = "-".join(hexes) + ".png"
    hexes_no_fe0f = [hex_value for hex_value in hexes if hex_value != "fe0f"]
    drop = "-".join(hexes_no_fe0f) + ".png" if hexes_no_fe0f != hexes else ""
    candidates = [keep]
    if drop and drop not in candidates:
        candidates.append(drop)
    return candidates


def _resolve_emoji_png(
    grapheme: str,
    emoji_image_dir: Path,
    emoji_auto_download: bool,
    emoji_base_url: str | None,
) -> Path | None:
    cache_key = (emoji_image_dir, grapheme)
    if cache_key in _EMOJI_PNG_CACHE:
        return _EMOJI_PNG_CACHE[cache_key]

    for name in _twemoji_filename_candidates(grapheme):
        candidate = emoji_image_dir / name
        if candidate.exists():
            _EMOJI_PNG_CACHE[cache_key] = candidate
            return candidate

    if emoji_auto_download and emoji_base_url:
        for name in _twemoji_filename_candidates(grapheme):
            candidate = emoji_image_dir / name
            if candidate.exists():
                _EMOJI_PNG_CACHE[cache_key] = candidate
                return candidate
            if _download_twemoji(candidate, emoji_base_url, name):
                _EMOJI_PNG_CACHE[cache_key] = candidate
                return candidate

    _EMOJI_PNG_CACHE[cache_key] = None
    return None


def _download_twemoji(destination: Path, base_url: str, filename: str) -> bool:
    url = f"{base_url.rstrip('/')}/{filename}"
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError:
        return False

    content_type = response.headers.get("Content-Type", "")
    if "image" not in content_type:
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return True


def _format_emoji_image_tag(path: Path, size: float, valign: str) -> str:
    src = _xml_attr(str(path))
    return f'<img src="{src}" width="{size:.2f}" height="{size:.2f}" valign="{valign}"/>'


def _xml_attr(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def _split_label_value(line: str) -> tuple[str, str]:
    label, _, value = line.partition(":")
    return label.strip(), value.strip()


def _format_labeled_line(
    label: str,
    value: str,
    bold_font_name: str | None,
    emoji_image_dir: Path | None,
    emoji_auto_download: bool,
    emoji_base_url: str | None,
    emoji_image_scale: float,
    emoji_image_valign: str,
    font_size: float,
) -> str:
    label_text = _format_paragraph_text(
        label,
        emoji_image_dir=emoji_image_dir,
        emoji_auto_download=emoji_auto_download,
        emoji_base_url=emoji_base_url,
        emoji_image_scale=emoji_image_scale,
        emoji_image_valign=emoji_image_valign,
        font_size=font_size,
    )
    value_text = _format_paragraph_text(
        value,
        emoji_image_dir=emoji_image_dir,
        emoji_auto_download=emoji_auto_download,
        emoji_base_url=emoji_base_url,
        emoji_image_scale=emoji_image_scale,
        emoji_image_valign=emoji_image_valign,
        font_size=font_size,
    )
    if bold_font_name:
        label_text = f'<font name="{bold_font_name}">{label_text}</font>'
    return f"{label_text}: {value_text}"
