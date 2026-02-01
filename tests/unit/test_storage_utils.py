"""Tests for storage CLI utilities."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from src.cli.storage.utils import (
    ExitCode,
    Output,
    handle_storage_errors,
    with_parquet_root,
    with_raw_dir,
)


class TestExitCode:
    """Tests for ExitCode enum."""

    def test_success_is_zero(self) -> None:
        """SUCCESS 应该是 0。"""
        assert ExitCode.SUCCESS == 0

    def test_general_error_is_one(self) -> None:
        """GENERAL_ERROR 应该是 1。"""
        assert ExitCode.GENERAL_ERROR == 1

    def test_invalid_argument_is_two(self) -> None:
        """INVALID_ARGUMENT 应该是 2。"""
        assert ExitCode.INVALID_ARGUMENT == 2

    def test_user_interrupted_is_130(self) -> None:
        """USER_INTERRUPTED 应该是 130 (128 + SIGINT)。"""
        assert ExitCode.USER_INTERRUPTED == 130

    def test_exit_code_can_be_used_with_sys_exit(self) -> None:
        """ExitCode 应该可以直接用于 sys.exit()。"""
        runner = CliRunner()

        @click.command()
        def cmd() -> None:
            raise SystemExit(ExitCode.FILE_NOT_FOUND)

        result = runner.invoke(cmd)
        assert result.exit_code == 66

    def test_all_exit_codes_are_unique(self) -> None:
        """所有退出码应该是唯一的。"""
        values = [code.value for code in ExitCode]
        assert len(values) == len(set(values))


class TestWithParquetRoot:
    """Tests for with_parquet_root decorator."""

    def test_uses_provided_parquet_root(self) -> None:
        """当提供 parquet_root 时，应使用提供的值。"""

        @with_parquet_root
        def sample_func(parquet_root: str) -> str:
            return parquet_root

        result = sample_func(parquet_root="/custom/path")
        assert result == "/custom/path"

    def test_uses_config_when_parquet_root_is_none(self, tmp_path: Any) -> None:
        """当 parquet_root 为 None 时，应从配置读取。"""
        expected_path = tmp_path / "parquet"

        @with_parquet_root
        def sample_func(parquet_root: str) -> str:
            return parquet_root

        with patch("src.config.get_messages_parquet_path", return_value=expected_path):
            result = sample_func(parquet_root=None)
            assert result == str(expected_path)

    def test_preserves_other_arguments(self) -> None:
        """应保留其他参数。"""

        @with_parquet_root
        def sample_func(start: str, end: str, parquet_root: str) -> dict[str, str]:
            return {"start": start, "end": end, "parquet_root": parquet_root}

        result = sample_func(start="2026-01-01", end="2026-01-31", parquet_root="/path")
        assert result == {
            "start": "2026-01-01",
            "end": "2026-01-31",
            "parquet_root": "/path",
        }


class TestWithRawDir:
    """Tests for with_raw_dir decorator."""

    def test_uses_provided_raw_dir(self) -> None:
        """当提供 raw_dir 时，应使用提供的值。"""

        @with_raw_dir
        def sample_func(raw_dir: str) -> str:
            return raw_dir

        result = sample_func(raw_dir="/custom/raw")
        assert result == "/custom/raw"

    def test_uses_config_when_raw_dir_is_none(self, tmp_path: Any) -> None:
        """当 raw_dir 为 None 时，应从配置读取。"""
        expected_path = tmp_path / "raw"

        @with_raw_dir
        def sample_func(raw_dir: str) -> str:
            return raw_dir

        with patch("src.config.get_messages_raw_path", return_value=expected_path):
            result = sample_func(raw_dir=None)
            assert result == str(expected_path)


class TestHandleStorageErrors:
    """Tests for handle_storage_errors decorator."""

    def test_passes_through_on_success(self) -> None:
        """成功时应正常返回结果。"""

        @handle_storage_errors("测试操作")
        def sample_func() -> str:
            return "success"

        result = sample_func()
        assert result == "success"

    def test_catches_exception_and_exits(self) -> None:
        """捕获异常时应输出错误并退出。"""

        @handle_storage_errors("测试操作")
        def sample_func() -> None:
            raise ValueError("测试错误")

        with pytest.raises(SystemExit) as exc_info:
            sample_func()
        assert exc_info.value.code == 1

    def test_preserves_system_exit(self) -> None:
        """应保留 SystemExit 异常。"""

        @handle_storage_errors("测试操作")
        def sample_func() -> None:
            raise SystemExit(42)

        with pytest.raises(SystemExit) as exc_info:
            sample_func()
        assert exc_info.value.code == 42

    def test_logs_exception(self) -> None:
        """应记录异常日志。"""

        @handle_storage_errors("测试操作")
        def sample_func() -> None:
            raise ValueError("测试错误")

        with patch("src.cli.storage.utils.logger") as mock_logger:
            with pytest.raises(SystemExit):
                sample_func()
            mock_logger.exception.assert_called_once()


class TestOutput:
    """Tests for Output class."""

    def test_success_basic(self) -> None:
        """success 应输出带 ✓ 前缀的消息。"""
        runner = CliRunner()

        @click.command()
        def cmd() -> None:
            Output.success("操作完成")

        result = runner.invoke(cmd)
        assert "✓ 操作完成" in result.output

    def test_success_with_details(self) -> None:
        """success 应输出附加详情。"""
        runner = CliRunner()

        @click.command()
        def cmd() -> None:
            Output.success("操作完成", 记录数=100, 耗时="2s")

        result = runner.invoke(cmd)
        assert "✓ 操作完成" in result.output
        assert "记录数: 100" in result.output
        assert "耗时: 2s" in result.output

    def test_error(self) -> None:
        """error 应输出带 ✗ 前缀的错误消息。"""
        runner = CliRunner()

        @click.command()
        def cmd() -> None:
            Output.error("操作失败")

        result = runner.invoke(cmd)
        # 错误输出到 stderr，但 CliRunner 会捕获
        assert "✗ 操作失败" in result.output

    def test_warning(self) -> None:
        """warning 应输出带 ⚠ 前缀的警告消息。"""
        runner = CliRunner()

        @click.command()
        def cmd() -> None:
            Output.warning("注意事项")

        result = runner.invoke(cmd)
        assert "⚠ 注意事项" in result.output

    def test_info(self) -> None:
        """info 应输出普通消息。"""
        runner = CliRunner()

        @click.command()
        def cmd() -> None:
            Output.info("普通信息")

        result = runner.invoke(cmd)
        assert "普通信息" in result.output

    def test_separator(self) -> None:
        """separator 应输出分隔线。"""
        runner = CliRunner()

        @click.command()
        def cmd() -> None:
            Output.separator()

        result = runner.invoke(cmd)
        assert "=" * 60 in result.output

    def test_separator_custom(self) -> None:
        """separator 应支持自定义字符和宽度。"""
        runner = CliRunner()

        @click.command()
        def cmd() -> None:
            Output.separator(char="-", width=40)

        result = runner.invoke(cmd)
        assert "-" * 40 in result.output

    def test_table_row(self) -> None:
        """table_row 应输出格式化的表格行。"""
        runner = CliRunner()

        @click.command()
        def cmd() -> None:
            Output.table_row("文件数量", 10)

        result = runner.invoke(cmd)
        assert "  文件数量: 10" in result.output
