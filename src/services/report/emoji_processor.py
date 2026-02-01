"""Emoji 处理器

处理文本中的 emoji，将其转换为图片标签。
"""

from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

import httpx

try:
    import regex as regex_module
except ImportError:
    regex_module = None

# Emoji 正则表达式
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

# 使用 regex 模块的高级正则（如果可用）
_GRAPHEME_RE = regex_module.compile(r"\X") if regex_module else None
_EMOJI_LIKE_RE = (
    regex_module.compile(r"(\p{Extended_Pictographic}|\p{Emoji_Presentation})")
    if regex_module
    else None
)

# 默认 Twemoji CDN URL
DEFAULT_TWEMOJI_BASE_URL = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72"


class EmojiProcessor:
    """Emoji 处理器

    处理文本中的 emoji，将其转换为图片标签。
    """

    def __init__(
        self,
        image_dir: Path | None = None,
        auto_download: bool = False,
        base_url: str = DEFAULT_TWEMOJI_BASE_URL,
        image_scale: float = 0.8,
        image_valign: str = "middle",
    ) -> None:
        """初始化 Emoji 处理器

        Args:
            image_dir: emoji 图片目录
            auto_download: 是否自动下载缺失的 emoji
            base_url: Twemoji CDN 基础 URL
            image_scale: 图片缩放比例
            image_valign: 图片垂直对齐方式
        """
        self.image_dir = image_dir
        self.auto_download = auto_download
        self.base_url = base_url.rstrip("/")
        self.image_scale = image_scale
        self.image_valign = image_valign
        self._cache: dict[str, Path | None] = {}

    def format_text(self, text: str, font_size: float) -> str:
        """格式化文本，将 emoji 替换为图片标签

        Args:
            text: 原始文本
            font_size: 字体大小

        Returns:
            格式化后的文本
        """
        if not self.image_dir:
            return escape(text)

        parts: list[str] = []
        for grapheme in self.split_graphemes(text):
            if self.looks_like_emoji(grapheme):
                png_path = self.resolve_emoji_png(grapheme)
                if png_path:
                    size = font_size * self.image_scale
                    parts.append(self.format_emoji_image_tag(png_path, size, self.image_valign))
                    continue
            parts.append(escape(grapheme))

        return "".join(parts)

    def split_graphemes(self, text: str) -> list[str]:
        """将文本分割为字素

        Args:
            text: 原始文本

        Returns:
            字素列表
        """
        if _GRAPHEME_RE:
            return [str(part) for part in _GRAPHEME_RE.findall(text)]
        return list(text)

    def looks_like_emoji(self, grapheme: str) -> bool:
        """判断字素是否像 emoji

        Args:
            grapheme: 字素

        Returns:
            是否像 emoji
        """
        if _EMOJI_LIKE_RE:
            return bool(_EMOJI_LIKE_RE.search(grapheme))
        return bool(_EMOJI_RE.search(grapheme))

    def twemoji_filename_candidates(self, grapheme: str) -> list[str]:
        """生成 Twemoji 文件名候选列表

        Args:
            grapheme: emoji 字素

        Returns:
            文件名候选列表
        """
        codepoints = [ord(ch) for ch in grapheme]
        hexes = [f"{cp:x}" for cp in codepoints]
        keep = "-".join(hexes) + ".png"
        hexes_no_fe0f = [hex_value for hex_value in hexes if hex_value != "fe0f"]
        drop = "-".join(hexes_no_fe0f) + ".png" if hexes_no_fe0f != hexes else ""
        candidates = [keep]
        if drop and drop not in candidates:
            candidates.append(drop)
        return candidates

    def resolve_emoji_png(self, grapheme: str) -> Path | None:
        """解析 emoji 图片路径

        Args:
            grapheme: emoji 字素

        Returns:
            图片路径，不存在返回 None
        """
        if not self.image_dir:
            return None

        cache_key = grapheme
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 搜索本地文件
        for name in self.twemoji_filename_candidates(grapheme):
            candidate = self.image_dir / name
            if candidate.exists():
                self._cache[cache_key] = candidate
                return candidate

        # 尝试下载
        if self.auto_download:
            for name in self.twemoji_filename_candidates(grapheme):
                candidate = self.image_dir / name
                if candidate.exists():
                    self._cache[cache_key] = candidate
                    return candidate
                if self.download_twemoji(name):
                    self._cache[cache_key] = candidate
                    return candidate

        self._cache[cache_key] = None
        return None

    def download_twemoji(self, filename: str) -> bool:
        """下载 Twemoji 图片

        Args:
            filename: 文件名

        Returns:
            是否下载成功
        """
        if not self.image_dir:
            return False

        url = f"{self.base_url}/{filename}"
        destination = self.image_dir / filename

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

    def format_emoji_image_tag(self, path: Path, size: float, valign: str) -> str:
        """格式化 emoji 图片标签

        Args:
            path: 图片路径
            size: 图片大小
            valign: 垂直对齐方式

        Returns:
            HTML 图片标签
        """
        src = self._xml_attr(str(path))
        return f'<img src="{src}" width="{size:.2f}" height="{size:.2f}" valign="{valign}"/>'

    def _xml_attr(self, value: str) -> str:
        """转义 XML 属性值

        Args:
            value: 原始值

        Returns:
            转义后的值
        """
        return escape(value, {'"': "&quot;"})
