"""Tests for storage ingestion CLI commands."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from src.cli.storage.ingestion_commands import dump_parquet, ingest_message


def _sample_message(timestamp: int, msg_id: str = "msg-1") -> dict[str, object]:
    """创建测试消息。"""
    return {
        "msg_id": msg_id,
        "from_username": "user_a",
        "to_username": "user_b",
        "chatroom": "",
        "chatroom_sender": "",
        "msg_type": 1,
        "create_time": timestamp,
        "is_chatroom_msg": 0,
        "content": "hello",
        "desc": "",
        "source": "api",
        "guid": f"guid-{msg_id}",
        "notify_type": 1,
    }


def _partition_path(parquet_root: Path, timestamp: int, filename: str) -> Path:
    """获取分区路径。"""
    dt = datetime.fromtimestamp(timestamp, tz=UTC)
    return (
        parquet_root / f"year={dt.year}" / f"month={dt.month:02d}" / f"day={dt.day:02d}" / filename
    )


class TestIngestMessageCommand:
    """Tests for ingest-message command."""

    def test_ingest_message_via_argument(self, tmp_path: Path) -> None:
        """应能通过 --message 参数入库消息。"""
        runner = CliRunner()
        parquet_root = tmp_path / "parquet"
        timestamp = 1_700_000_000
        payload = _sample_message(timestamp)

        result = runner.invoke(
            ingest_message,
            [
                "--message",
                json.dumps(payload, ensure_ascii=False),
                "--parquet-root",
                str(parquet_root),
            ],
        )

        assert result.exit_code == 0, result.output
        parquet_file = _partition_path(parquet_root, timestamp, "data.parquet")
        assert parquet_file.exists()
        assert "写入完成" in result.output

    def test_ingest_message_via_stdin(self, tmp_path: Path) -> None:
        """应能通过 stdin 入库消息。"""
        runner = CliRunner()
        parquet_root = tmp_path / "parquet"
        timestamp = 1_700_000_000
        payload = _sample_message(timestamp)

        result = runner.invoke(
            ingest_message,
            [
                "--parquet-root",
                str(parquet_root),
            ],
            input=json.dumps(payload, ensure_ascii=False),
        )

        assert result.exit_code == 0, result.output
        parquet_file = _partition_path(parquet_root, timestamp, "data.parquet")
        assert parquet_file.exists()

    def test_ingest_message_via_file(self, tmp_path: Path) -> None:
        """应能通过文件入库消息。"""
        runner = CliRunner()
        parquet_root = tmp_path / "parquet"
        message_file = tmp_path / "message.json"
        timestamp = 1_700_000_000
        payload = _sample_message(timestamp)

        message_file.write_text(json.dumps(payload, ensure_ascii=False))

        result = runner.invoke(
            ingest_message,
            [
                "--message-file",
                str(message_file),
                "--parquet-root",
                str(parquet_root),
            ],
        )

        assert result.exit_code == 0, result.output
        parquet_file = _partition_path(parquet_root, timestamp, "data.parquet")
        assert parquet_file.exists()

    def test_ingest_message_with_raw_file(self, tmp_path: Path) -> None:
        """应能写入 JSONL 并使用检查点。"""
        runner = CliRunner()
        parquet_root = tmp_path / "parquet"
        raw_file = tmp_path / "raw" / "messages.jsonl"
        checkpoint_dir = tmp_path / "checkpoints"
        timestamp = 1_700_000_123
        payload = _sample_message(timestamp)

        result = runner.invoke(
            ingest_message,
            [
                "--message",
                json.dumps(payload, ensure_ascii=False),
                "--parquet-root",
                str(parquet_root),
                "--raw-file",
                str(raw_file),
                "--checkpoint-dir",
                str(checkpoint_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        assert raw_file.exists()
        parquet_file = _partition_path(parquet_root, timestamp, "part-0.parquet")
        assert parquet_file.exists()

    def test_ingest_message_invalid_json(self, tmp_path: Path) -> None:
        """无效 JSON 应报错。"""
        runner = CliRunner()
        parquet_root = tmp_path / "parquet"

        result = runner.invoke(
            ingest_message,
            [
                "--message",
                "not valid json",
                "--parquet-root",
                str(parquet_root),
            ],
        )

        assert result.exit_code == 1
        assert "JSON 解析失败" in result.output

    def test_ingest_message_no_input(self, tmp_path: Path) -> None:
        """无输入时应报错。"""
        runner = CliRunner()
        parquet_root = tmp_path / "parquet"

        result = runner.invoke(
            ingest_message,
            [
                "--parquet-root",
                str(parquet_root),
            ],
        )

        assert result.exit_code == 1
        assert "未提供消息" in result.output

    def test_ingest_message_conflict_options(self, tmp_path: Path) -> None:
        """--message 和 --message-file 不能同时使用。"""
        runner = CliRunner()
        parquet_root = tmp_path / "parquet"
        message_file = tmp_path / "message.json"
        message_file.write_text("{}")

        result = runner.invoke(
            ingest_message,
            [
                "--message",
                "{}",
                "--message-file",
                str(message_file),
                "--parquet-root",
                str(parquet_root),
            ],
        )

        assert result.exit_code == 1
        assert "不能同时使用" in result.output


class TestDumpParquetCommand:
    """Tests for dump-parquet command."""

    def test_dump_parquet_basic(self, tmp_path: Path) -> None:
        """应能转换 JSONL 到 Parquet。"""
        runner = CliRunner()
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        checkpoint_dir = tmp_path / "checkpoints"

        raw_dir.mkdir(parents=True)
        timestamp = 1_700_000_000
        jsonl_file = raw_dir / "messages.jsonl"
        jsonl_file.write_text(
            json.dumps(_sample_message(timestamp, "msg-1"))
            + "\n"
            + json.dumps(_sample_message(timestamp + 60, "msg-2"))
            + "\n"
        )

        result = runner.invoke(
            dump_parquet,
            [
                "--raw-dir",
                str(raw_dir),
                "--parquet-root",
                str(parquet_root),
                "--checkpoint-dir",
                str(checkpoint_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        assert "转换完成" in result.output
        assert "总新增: 2" in result.output

    def test_dump_parquet_no_files(self, tmp_path: Path) -> None:
        """无 JSONL 文件时应报错。"""
        runner = CliRunner()
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"

        raw_dir.mkdir(parents=True)

        result = runner.invoke(
            dump_parquet,
            [
                "--raw-dir",
                str(raw_dir),
                "--parquet-root",
                str(parquet_root),
            ],
        )

        assert result.exit_code == 1
        assert "未找到 JSONL 文件" in result.output

    def test_dump_parquet_with_deduplication(self, tmp_path: Path) -> None:
        """应支持去重选项。"""
        runner = CliRunner()
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        checkpoint_dir = tmp_path / "checkpoints"

        raw_dir.mkdir(parents=True)
        timestamp = 1_700_000_000
        jsonl_file = raw_dir / "messages.jsonl"
        # 写入重复消息
        jsonl_file.write_text(
            json.dumps(_sample_message(timestamp, "msg-1"))
            + "\n"
            + json.dumps(_sample_message(timestamp, "msg-1"))
            + "\n"  # 重复
        )

        result = runner.invoke(
            dump_parquet,
            [
                "--raw-dir",
                str(raw_dir),
                "--parquet-root",
                str(parquet_root),
                "--checkpoint-dir",
                str(checkpoint_dir),
                "--deduplicate",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "跳过重复" in result.output
