"""FontManager 单元测试"""

from pathlib import Path
from unittest.mock import patch

import pytest
from diting.services.report.font_manager import FontManager, font_search_dirs


class TestFontSearchDirs:
    """字体搜索目录测试"""

    def test_returns_list_of_paths(self) -> None:
        """测试返回路径列表"""
        dirs = font_search_dirs()
        assert isinstance(dirs, list)
        assert all(isinstance(d, Path) for d in dirs)

    def test_includes_common_directories(self) -> None:
        """测试包含常见目录"""
        dirs = font_search_dirs()
        dir_strs = [str(d) for d in dirs]
        # 应该包含项目目录
        assert any("assets" in d or "fonts" in d for d in dir_strs)


class TestFontManager:
    """FontManager 测试"""

    def test_init_with_defaults(self) -> None:
        """测试默认初始化"""
        manager = FontManager()
        assert manager.font_name == "SourceHanSans"
        assert manager.bold_font_name == "SourceHanSans-Bold"

    def test_init_with_custom_names(self) -> None:
        """测试自定义字体名称"""
        manager = FontManager(font_name="CustomFont", bold_font_name="CustomBold")
        assert manager.font_name == "CustomFont"
        assert manager.bold_font_name == "CustomBold"

    def test_resolve_font_path_from_env(self, tmp_path: Path) -> None:
        """测试从环境变量解析字体路径"""
        font_file = tmp_path / "test.ttf"
        font_file.touch()

        with patch.dict("os.environ", {"SOURCE_HAN_SANS_PATH": str(font_file)}):
            manager = FontManager()
            result = manager.resolve_font_path(None)
            assert result == font_file

    def test_resolve_font_path_explicit(self, tmp_path: Path) -> None:
        """测试显式指定字体路径"""
        font_file = tmp_path / "explicit.ttf"
        font_file.touch()

        manager = FontManager()
        result = manager.resolve_font_path(font_file)
        assert result == font_file

    def test_resolve_font_path_not_found(self, tmp_path: Path) -> None:
        """测试字体文件不存在时抛出异常"""
        manager = FontManager()
        with pytest.raises(FileNotFoundError):
            manager.resolve_font_path(tmp_path / "nonexistent.ttf")

    def test_resolve_bold_font_path_from_env(self, tmp_path: Path) -> None:
        """测试从环境变量解析粗体字体路径"""
        bold_file = tmp_path / "bold.ttf"
        bold_file.touch()

        with patch.dict("os.environ", {"SOURCE_HAN_SANS_BOLD_PATH": str(bold_file)}):
            manager = FontManager()
            result = manager.resolve_bold_font_path(tmp_path)
            assert result == bold_file

    def test_resolve_bold_font_path_not_found(self, tmp_path: Path) -> None:
        """测试粗体字体不存在时返回 None"""
        manager = FontManager()
        result = manager.resolve_bold_font_path(tmp_path)
        assert result is None

    def test_resolve_bold_font_path_auto_detect(self, tmp_path: Path) -> None:
        """测试自动检测粗体字体"""
        # 创建常规字体文件
        regular_file = tmp_path / "SourceHanSansSC-Regular.ttf"
        regular_file.touch()
        # 创建粗体字体文件
        bold_file = tmp_path / "SourceHanSansSC-Bold.ttf"
        bold_file.touch()

        manager = FontManager()
        result = manager.resolve_bold_font_path(regular_file)
        assert result == bold_file
