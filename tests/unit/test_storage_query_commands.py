"""Tests for storage query CLI commands."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from click.testing import CliRunner
from diting.cli.storage.query_commands import query, query_by_id


def _create_test_parquet(parquet_root: Path, timestamp: int) -> Path:
    """创建测试用 Parquet 文件。"""
    dt = datetime.fromtimestamp(timestamp, tz=UTC)
    partition_dir = parquet_root / f"year={dt.year}" / f"month={dt.month:02d}" / f"day={dt.day:02d}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(
        [
            {
                "msg_id": "msg-1",
                "from_username": "user_a",
                "to_username": "user_b",
                "chatroom": "room_1",
                "msg_type": 1,
                "create_time": timestamp,
                "content": "hello",
            },
            {
                "msg_id": "msg-2",
                "from_username": "user_b",
                "to_username": "user_a",
                "chatroom": "room_1",
                "msg_type": 1,
                "create_time": timestamp + 60,
                "content": "world",
            },
        ]
    )

    parquet_file = partition_dir / "data.parquet"
    df.to_parquet(parquet_file)
    return parquet_file


class TestQueryCommand:
    """Tests for query command."""

    def test_query_with_date_range(self, tmp_path: Path) -> None:
        """应能按日期范围查询消息。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000  # 2023-11-14
        _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            query,
            [
                "--start",
                "2023-11-14",
                "--end",
                "2023-11-15",
                "--parquet-root",
                str(parquet_root),
            ],
        )

        assert result.exit_code == 0, result.output
        assert "2 条记录" in result.output

    def test_query_with_chatroom_filter(self, tmp_path: Path) -> None:
        """应能按群聊过滤。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000
        _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            query,
            [
                "--start",
                "2023-11-14",
                "--end",
                "2023-11-15",
                "--parquet-root",
                str(parquet_root),
                "--chatroom",
                "room_1",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "2 条记录" in result.output

    def test_query_with_limit(self, tmp_path: Path) -> None:
        """应能限制返回记录数。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000
        _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            query,
            [
                "--start",
                "2023-11-14",
                "--end",
                "2023-11-15",
                "--parquet-root",
                str(parquet_root),
                "--limit",
                "1",
            ],
        )

        assert result.exit_code == 0, result.output

    def test_query_export_csv(self, tmp_path: Path) -> None:
        """应能导出为 CSV。"""
        parquet_root = tmp_path / "parquet"
        output_file = tmp_path / "output.csv"
        timestamp = 1700000000
        _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            query,
            [
                "--start",
                "2023-11-14",
                "--end",
                "2023-11-15",
                "--parquet-root",
                str(parquet_root),
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0, result.output
        assert output_file.exists()
        assert "已导出" in result.output

    def test_query_no_results(self, tmp_path: Path) -> None:
        """查询不匹配的日期范围时应显示提示。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000  # 2023-11-14
        _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        # 查询一个没有数据的日期范围
        result = runner.invoke(
            query,
            [
                "--start",
                "2023-01-01",
                "--end",
                "2023-01-02",
                "--parquet-root",
                str(parquet_root),
            ],
        )

        assert result.exit_code == 0, result.output
        assert "0 条记录" in result.output or "未找到" in result.output

    def test_query_uses_default_parquet_root(self, tmp_path: Path) -> None:
        """未指定 parquet_root 时应使用配置默认值。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000
        _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        with patch("diting.config.get_messages_parquet_path", return_value=parquet_root):
            result = runner.invoke(
                query,
                [
                    "--start",
                    "2023-11-14",
                    "--end",
                    "2023-11-15",
                ],
            )

        assert result.exit_code == 0, result.output


class TestQueryByIdCommand:
    """Tests for query-by-id command."""

    def test_query_single_id(self, tmp_path: Path) -> None:
        """应能查询单个消息 ID。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000
        _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            query_by_id,
            [
                "msg-1",
                "--parquet-root",
                str(parquet_root),
            ],
        )

        assert result.exit_code == 0, result.output
        assert "1 条记录" in result.output

    def test_query_multiple_ids(self, tmp_path: Path) -> None:
        """应能查询多个消息 ID。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000
        _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            query_by_id,
            [
                "msg-1",
                "msg-2",
                "--parquet-root",
                str(parquet_root),
            ],
        )

        assert result.exit_code == 0, result.output
        assert "2 条记录" in result.output

    def test_query_by_id_export_csv(self, tmp_path: Path) -> None:
        """应能导出为 CSV。"""
        parquet_root = tmp_path / "parquet"
        output_file = tmp_path / "output.csv"
        timestamp = 1700000000
        _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            query_by_id,
            [
                "msg-1",
                "--parquet-root",
                str(parquet_root),
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0, result.output
        assert output_file.exists()

    def test_query_by_id_not_found(self, tmp_path: Path) -> None:
        """查询不存在的 ID 时应显示提示。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000
        _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            query_by_id,
            [
                "nonexistent-id",
                "--parquet-root",
                str(parquet_root),
            ],
        )

        assert result.exit_code == 0, result.output
        assert "0 条记录" in result.output or "未找到" in result.output
