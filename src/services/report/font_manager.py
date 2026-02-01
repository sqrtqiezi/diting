"""字体管理器

管理 PDF 渲染所需的字体文件解析和注册。
"""

from __future__ import annotations

import os
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont


def font_search_dirs() -> list[Path]:
    """获取字体搜索目录列表

    Returns:
        字体搜索目录列表
    """
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


class FontManager:
    """字体管理器

    管理 PDF 渲染所需的字体文件解析和注册。
    """

    # 常规字体候选文件名
    REGULAR_CANDIDATES = [
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

    # 粗体字体候选文件名
    BOLD_CANDIDATES = [
        "SourceHanSansSC-Bold.ttc",
        "SourceHanSansCN-Bold.ttc",
        "SourceHanSans-Bold.ttc",
        "SourceHanSansSC-Bold.ttf",
        "SourceHanSansCN-Bold.ttf",
        "SourceHanSans-Bold.ttf",
    ]

    def __init__(
        self,
        font_name: str = "SourceHanSans",
        bold_font_name: str = "SourceHanSans-Bold",
    ) -> None:
        """初始化字体管理器

        Args:
            font_name: 常规字体注册名称
            bold_font_name: 粗体字体注册名称
        """
        self.font_name = font_name
        self.bold_font_name = bold_font_name

    def resolve_font_path(self, font_path: Path | None) -> Path:
        """解析常规字体路径

        Args:
            font_path: 显式指定的字体路径，为 None 时自动搜索

        Returns:
            字体文件路径

        Raises:
            FileNotFoundError: 字体文件不存在
        """
        if font_path:
            if font_path.exists():
                return font_path
            raise FileNotFoundError(f"指定字体文件不存在: {font_path}")

        # 从环境变量获取
        env_path = os.environ.get("SOURCE_HAN_SANS_PATH")
        if env_path:
            candidate = Path(env_path).expanduser()
            if candidate.exists():
                return candidate

        # 搜索常见目录
        search_dirs = font_search_dirs()
        for directory in search_dirs:
            for name in self.REGULAR_CANDIDATES:
                candidate = directory / name
                if candidate.exists():
                    return candidate
            # 尝试 glob 匹配
            for glob in ("SourceHanSans*.ttc", "SourceHanSans*.ttf", "SourceHanSans*.otf"):
                matches = list(directory.glob(glob))
                if matches:
                    return matches[0]

        searched = ", ".join(str(path) for path in search_dirs)
        raise FileNotFoundError(
            "未找到思源黑体字体文件，请下载 Source Han Sans 并放到以下目录之一: "
            f"{searched}. 也可以通过 --font-path 或 SOURCE_HAN_SANS_PATH 指定字体路径。"
        )

    def resolve_bold_font_path(self, regular_path: Path) -> Path | None:
        """解析粗体字体路径

        Args:
            regular_path: 常规字体路径，用于确定搜索目录

        Returns:
            粗体字体文件路径，不存在返回 None
        """
        # 从环境变量获取
        env_path = os.environ.get("SOURCE_HAN_SANS_BOLD_PATH")
        if env_path:
            candidate = Path(env_path).expanduser()
            if candidate.exists():
                return candidate

        # 搜索常见目录
        search_dirs = [regular_path.parent] + font_search_dirs()
        for directory in search_dirs:
            for name in self.BOLD_CANDIDATES:
                candidate = directory / name
                if candidate.exists():
                    return candidate
            # 尝试 glob 匹配
            for glob in ("SourceHanSans*Bold*.ttc", "SourceHanSans*Bold*.ttf"):
                matches = list(directory.glob(glob))
                if matches:
                    return matches[0]

        return None

    def register_font(self, font_path: Path, name: str, font_index: int | None = None) -> str:
        """注册字体

        Args:
            font_path: 字体文件路径
            name: 注册名称
            font_index: TTC 字体的子字体索引

        Returns:
            注册的字体名称

        Raises:
            ValueError: 字体格式不支持
        """
        if name in pdfmetrics.getRegisteredFontNames():
            return name

        suffix = font_path.suffix.lower()
        try:
            if suffix == ".ttc":
                subfont_index = 0 if font_index is None else font_index
                pdfmetrics.registerFont(TTFont(name, str(font_path), subfontIndex=subfont_index))
            else:
                pdfmetrics.registerFont(TTFont(name, str(font_path)))
        except TTFError as exc:
            message = str(exc)
            if "postscript outlines are not supported" in message:
                raise ValueError(
                    "检测到 CFF 轮廓的 OTF 字体，ReportLab 不支持该格式。"
                    "请改用 TrueType 轮廓的 TTF/TTC 版本的思源黑体，"
                    "或使用 --font-path 指向可用的 TTF/TTC 字体。"
                ) from exc
            raise
        return name

    def setup_fonts(
        self,
        font_path: Path | None = None,
        font_index: int | None = None,
    ) -> tuple[str, str]:
        """设置字体

        解析并注册常规字体和粗体字体。

        Args:
            font_path: 显式指定的字体路径
            font_index: TTC 字体的子字体索引

        Returns:
            (常规字体名称, 粗体字体名称) 元组
        """
        resolved_font_path = self.resolve_font_path(font_path)
        registered_name = self.register_font(resolved_font_path, self.font_name, font_index)

        bold_name = registered_name
        resolved_bold_path = self.resolve_bold_font_path(resolved_font_path)
        if resolved_bold_path:
            bold_name = self.register_font(resolved_bold_path, self.bold_font_name, font_index)

        return registered_name, bold_name
