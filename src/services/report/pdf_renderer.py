"""Markdown to PDF rendering helpers for chatroom analysis reports.

这是一个 Facade 类，内部委托给各个模块处理具体操作。
保持向后兼容的公共 API。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, SimpleDocTemplate

from src.services.report.element_handlers import RenderContext, create_default_handlers
from src.services.report.emoji_processor import DEFAULT_TWEMOJI_BASE_URL, EmojiProcessor
from src.services.report.font_manager import FontManager
from src.services.report.style_builder import StyleBuilder

# 保持向后兼容的正则表达式
_TABLE_SEPARATOR_RE = re.compile(r"^[\s|:-]+$")
_NUMBERED_ITEM_RE = re.compile(r"^(\d+)\.\s+(.*)$")


@dataclass(frozen=True)
class PdfRenderOptions:
    """PDF 渲染选项"""

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
    emoji_base_url: str = DEFAULT_TWEMOJI_BASE_URL


def render_markdown_report_pdf(
    markdown_path: Path,
    output_path: Path,
    font_path: Path | None = None,
    font_index: int | None = None,
    emoji_image_dir: Path | None = None,
    options: PdfRenderOptions | None = None,
) -> None:
    """从 Markdown 文件渲染 PDF 报告

    Args:
        markdown_path: Markdown 文件路径
        output_path: 输出 PDF 路径
        font_path: 字体文件路径
        font_index: TTC 字体索引
        emoji_image_dir: emoji 图片目录
        options: 渲染选项
    """
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
    """从 Markdown 文本渲染 PDF

    Args:
        markdown_text: Markdown 文本
        output_path: 输出 PDF 路径
        font_path: 字体文件路径
        font_index: TTC 字体索引
        emoji_image_dir: emoji 图片目录
        options: 渲染选项
    """
    render_options = options or PdfRenderOptions()

    # 设置字体
    font_manager = FontManager()
    font_name, bold_font_name = font_manager.setup_fonts(font_path, font_index)

    # 设置 emoji 处理器
    auto_download = _emoji_auto_download_enabled(render_options.emoji_auto_download)
    resolved_emoji_dir = _resolve_emoji_image_dir(emoji_image_dir, auto_download=auto_download)
    emoji_base_url = _resolve_emoji_base_url(render_options.emoji_base_url)

    emoji_processor = EmojiProcessor(
        image_dir=resolved_emoji_dir,
        auto_download=auto_download,
        base_url=emoji_base_url,
        image_scale=render_options.emoji_image_scale,
        image_valign=render_options.emoji_image_valign,
    )

    # 构建样式
    style_builder = StyleBuilder(font_name, bold_font_name)
    styles = style_builder.build(render_options)

    # 构建 flowables
    flowables = _build_flowables_with_handlers(
        markdown_text,
        styles,
        render_options,
        emoji_processor,
        bold_font_name,
    )

    # 生成 PDF
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


def _build_flowables_with_handlers(
    markdown_text: str,
    styles: dict[str, ParagraphStyle],
    options: PdfRenderOptions,
    emoji_processor: EmojiProcessor,
    bold_font_name: str,
) -> list[Flowable]:
    """使用处理器构建 flowables

    Args:
        markdown_text: Markdown 文本
        styles: 样式字典
        options: 渲染选项
        emoji_processor: emoji 处理器
        bold_font_name: 粗体字体名称

    Returns:
        Flowable 列表
    """
    lines = markdown_text.splitlines()
    handlers = create_default_handlers()

    context = RenderContext(
        styles=styles,
        options=options,
        emoji_processor=emoji_processor,
        bold_font_name=bold_font_name,
        lines=lines,
    )

    flowables: list[Flowable] = []
    index = 0

    while index < len(lines):
        line = lines[index].rstrip()
        context.current_index = index

        if not line.strip():
            index += 1
            continue

        for handler in handlers:
            if handler.can_handle(line, context):
                result = handler.handle(line, context)
                flowables.extend(result)
                index += handler.lines_consumed()
                break
        else:
            index += 1

    return flowables


# ==================== 向后兼容的辅助函数 ====================


def _resolve_emoji_image_dir(emoji_dir: Path | None, auto_download: bool) -> Path | None:
    """解析 emoji 图片目录"""
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
    """检查是否启用 emoji 自动下载"""
    env_value = os.environ.get("EMOJI_AUTO_DOWNLOAD")
    if env_value is None:
        return default_enabled
    return env_value.strip().lower() not in {"0", "false", "no", "off"}


def _resolve_emoji_base_url(base_url: str) -> str:
    """解析 emoji 基础 URL"""
    env_value = os.environ.get("TWEMOJI_BASE_URL")
    if env_value:
        return env_value.strip().rstrip("/")
    return base_url.rstrip("/")


# ==================== 向后兼容的公共函数 ====================
# 这些函数保持原有签名，供外部调用


def _build_styles(
    font_name: str, bold_font_name: str, options: PdfRenderOptions
) -> dict[str, ParagraphStyle]:
    """构建样式（向后兼容）"""
    builder = StyleBuilder(font_name, bold_font_name)
    return builder.build(options)


def _is_table_line(line: str) -> bool:
    """判断是否为表格行"""
    stripped = line.strip()
    return stripped.startswith("|") and "|" in stripped[1:]


def _consume_table(lines: list[str], start_index: int) -> tuple[list[str], int]:
    """消费表格行"""
    table_lines: list[str] = []
    index = start_index
    while index < len(lines) and _is_table_line(lines[index]):
        table_lines.append(lines[index])
        index += 1
    return table_lines, index


def _split_table_row(line: str) -> list[str]:
    """分割表格行"""
    return [segment.strip() for segment in line.strip().strip("|").split("|")]


def _normalize_row(row: list[str], target_len: int) -> list[str]:
    """规范化表格行长度"""
    if len(row) < target_len:
        return row + [""] * (target_len - len(row))
    if len(row) > target_len:
        return row[:target_len]
    return row


def _table_col_widths(content_width: int, columns: int) -> list[float]:
    """计算表格列宽"""
    if columns == 7:
        ratios = [0.06, 0.36, 0.1, 0.12, 0.12, 0.12, 0.12]
    elif columns == 4:
        ratios = [0.1, 0.5, 0.2, 0.2]
    else:
        ratios = [1 / columns] * columns
    return [content_width * ratio for ratio in ratios]


def _split_graphemes(text: str) -> list[str]:
    """分割字素"""
    processor = EmojiProcessor()
    return processor.split_graphemes(text)


def _twemoji_filename_candidates(grapheme: str) -> list[str]:
    """生成 Twemoji 文件名候选"""
    processor = EmojiProcessor()
    return processor.twemoji_filename_candidates(grapheme)


def _split_label_value(line: str) -> tuple[str, str]:
    """分割标签和值"""
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
    """格式化带标签的行"""
    processor = EmojiProcessor(
        image_dir=emoji_image_dir,
        auto_download=emoji_auto_download,
        base_url=emoji_base_url or DEFAULT_TWEMOJI_BASE_URL,
        image_scale=emoji_image_scale,
        image_valign=emoji_image_valign,
    )

    label_text = processor.format_text(label, font_size)
    value_text = processor.format_text(value, font_size)

    if bold_font_name:
        label_text = f'<font name="{bold_font_name}">{label_text}</font>'

    return f"{label_text}: {value_text}"
