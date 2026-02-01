"""Tests for storage detect CLI commands."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from click.testing import CliRunner
from diting.cli.storage.detect_commands import detect_duplicates_cmd


def _create_test_parquet_with_duplicates(parquet_root: Path, timestamp: int) -> Path:
    """创建包含重复消息的测试 Parquet 文件。"""
    dt = datetime.fromtimestamp(timestamp, tz=UTC)
    partition_dir = parquet_root / f"year={dt.year}" / f"month={dt.month:02d}" / f"day={dt.day:02d}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(
        [
            {
                "msg_id": "msg-1",
                "from_username": "user_a",
                "to_username": "user_b",
                "msg_type": 1,
                "create_time": timestamp,
                "content": "hello",
            },
            {
                "msg_id": "msg-1",  # 重复
                "from_username": "user_a",
                "to_username": "user_b",
                "msg_type": 1,
                "create_time": timestamp,
                "content": "hello again",
            },
            {
                "msg_id": "msg-2",
                "from_username": "user_b",
                "to_username": "user_a",
                "msg_type": 1,
                "create_time": timestamp + 60,
                "content": "world",
            },
        ]
    )

    parquet_file = partition_dir / "data.parquet"
    df.to_parquet(parquet_file)
    return partition_dir


def _create_test_parquet_no_duplicates(parquet_root: Path, timestamp: int) -> Path:
    """创建无重复消息的测试 Parquet 文件。"""
    dt = datetime.fromtimestamp(timestamp, tz=UTC)
    partition_dir = parquet_root / f"year={dt.year}" / f"month={dt.month:02d}" / f"day={dt.day:02d}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(
        [
            {
                "msg_id": "msg-1",
                "from_username": "user_a",
                "to_username": "user_b",
                "msg_type": 1,
                "create_time": timestamp,
                "content": "hello",
            },
            {
                "msg_id": "msg-2",
                "from_username": "user_b",
                "to_username": "user_a",
                "msg_type": 1,
                "create_time": timestamp + 60,
                "content": "world",
            },
        ]
    )

    parquet_file = partition_dir / "data.parquet"
    df.to_parquet(parquet_file)
    return partition_dir


class TestDetectDuplicatesCommand:
    """Tests for detect-duplicates command."""

    def test_detect_no_duplicates(self, tmp_path: Path) -> None:
        """无重复时应显示成功消息。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000
        _create_test_parquet_no_duplicates(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            detect_duplicates_cmd,
            ["--parquet-root", str(parquet_root)],
        )

        assert result.exit_code == 0, result.output
        assert "未发现重复消息" in result.output

    def test_detect_with_duplicates(self, tmp_path: Path) -> None:
        """有重复时应显示警告并返回非零退出码。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000
        _create_test_parquet_with_duplicates(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            detect_duplicates_cmd,
            ["--parquet-root", str(parquet_root)],
        )

        assert result.exit_code == 1  # 发现重复应返回非零
        assert "发现" in result.output
        assert "重复" in result.output

    def test_detect_with_show_details(self, tmp_path: Path) -> None:
        """--show-details 应显示详细列表。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000
        _create_test_parquet_with_duplicates(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            detect_duplicates_cmd,
            ["--parquet-root", str(parquet_root), "--show-details"],
        )

        assert result.exit_code == 1
        assert "重复消息列表" in result.output
        assert "msg-1" in result.output

    def test_detect_export_csv(self, tmp_path: Path) -> None:
        """应能导出重复列表到 CSV。"""
        parquet_root = tmp_path / "parquet"
        output_file = tmp_path / "duplicates.csv"
        timestamp = 1700000000
        _create_test_parquet_with_duplicates(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            detect_duplicates_cmd,
            [
                "--parquet-root",
                str(parquet_root),
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 1  # 发现重复
        assert output_file.exists()
        assert "已导出" in result.output
