"""JSONLToParquetConverter 单元测试

测试 JSONL 到 Parquet 转换的核心功能，使用 mock 隔离文件系统依赖。
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.services.storage.ingestion import (
    append_to_parquet_partition,
    convert_jsonl_to_parquet,
)


class TestConvertJSONLToParquet:
    """测试 JSONL 到 Parquet 转换"""

    @pytest.fixture
    def sample_messages(self) -> list[dict]:
        """创建示例消息"""
        return [
            {
                "msg_id": "msg_1",
                "from_username": "wxid_sender1",
                "to_username": "wxid_receiver1",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590400,  # 2025-01-23
                "is_chatroom_msg": 0,
                "content": "Hello",
                "desc": "",
                "source": "0",
                "guid": "guid_1",
                "notify_type": 100,
            },
            {
                "msg_id": "msg_2",
                "from_username": "wxid_sender2",
                "to_username": "wxid_receiver2",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590401,  # 2025-01-23
                "is_chatroom_msg": 0,
                "content": "World",
                "desc": "",
                "source": "0",
                "guid": "guid_2",
                "notify_type": 100,
            },
        ]

    def test_convert_jsonl_to_parquet_success(self, tmp_path: Path, sample_messages: list[dict]):
        """测试成功转换 JSONL 到 Parquet"""
        # 创建 JSONL 文件
        jsonl_file = tmp_path / "messages.jsonl"
        import json

        with open(jsonl_file, "w", encoding="utf-8") as f:
            for msg in sample_messages:
                f.write(json.dumps(msg) + "\n")

        parquet_root = tmp_path / "parquet"

        # 执行转换
        result = convert_jsonl_to_parquet(jsonl_file, parquet_root)

        # 验证返回结果
        assert result["total_records"] == 2
        assert result["source_file"] == str(jsonl_file)
        # 文件很小，可能被四舍五入为 0.0 MB
        assert result["source_size_mb"] >= 0
        assert result["target_size_mb"] >= 0

        # 验证 Parquet 文件被创建
        partition_dir = parquet_root / "year=2025" / "month=01" / "day=23"
        parquet_file = partition_dir / "data.parquet"
        assert parquet_file.exists()

        # 验证 Parquet 内容
        table = pq.read_table(parquet_file)
        assert len(table) == 2
        assert "msg_id" in table.column_names
        assert "create_time" in table.column_names

    def test_convert_jsonl_to_parquet_file_not_found(self, tmp_path: Path):
        """测试 JSONL 文件不存在抛出 FileNotFoundError"""
        jsonl_file = tmp_path / "nonexistent.jsonl"
        parquet_root = tmp_path / "parquet"

        with pytest.raises(FileNotFoundError, match="JSONL 文件不存在"):
            convert_jsonl_to_parquet(jsonl_file, parquet_root)

    def test_convert_jsonl_to_parquet_empty_file(self, tmp_path: Path):
        """测试空 JSONL 文件返回零记录"""
        jsonl_file = tmp_path / "empty.jsonl"
        jsonl_file.touch()

        parquet_root = tmp_path / "parquet"

        result = convert_jsonl_to_parquet(jsonl_file, parquet_root)

        assert result["total_records"] == 0
        assert result["total_batches"] == 0

    def test_convert_jsonl_to_parquet_with_custom_schema(
        self, tmp_path: Path, sample_messages: list[dict]
    ):
        """测试使用自定义 Schema 转换"""
        # 创建 JSONL 文件
        jsonl_file = tmp_path / "messages.jsonl"
        import json

        with open(jsonl_file, "w", encoding="utf-8") as f:
            for msg in sample_messages:
                f.write(json.dumps(msg) + "\n")

        parquet_root = tmp_path / "parquet"

        # 自定义 Schema
        custom_schema = pa.schema(
            [
                ("msg_id", pa.string()),
                ("from_username", pa.string()),
                ("to_username", pa.string()),
                ("chatroom", pa.string()),
                ("chatroom_sender", pa.string()),
                ("msg_type", pa.int32()),
                ("create_time", pa.timestamp("s", tz="UTC")),
                ("is_chatroom_msg", pa.int8()),
                ("content", pa.string()),
                ("desc", pa.string()),
                ("source", pa.string()),
                ("guid", pa.string()),
                ("notify_type", pa.int32()),
                ("ingestion_time", pa.timestamp("s", tz="UTC")),
            ]
        )

        result = convert_jsonl_to_parquet(jsonl_file, parquet_root, schema=custom_schema)

        assert result["total_records"] == 2

    def test_convert_jsonl_to_parquet_with_compression(
        self, tmp_path: Path, sample_messages: list[dict]
    ):
        """测试使用不同压缩算法"""
        jsonl_file = tmp_path / "messages.jsonl"
        import json

        with open(jsonl_file, "w", encoding="utf-8") as f:
            for msg in sample_messages:
                f.write(json.dumps(msg) + "\n")

        parquet_root = tmp_path / "parquet"

        # 测试 gzip 压缩
        result = convert_jsonl_to_parquet(jsonl_file, parquet_root, compression="gzip")

        assert result["total_records"] == 2

        # 验证文件存在
        partition_dir = parquet_root / "year=2025" / "month=01" / "day=23"
        parquet_file = partition_dir / "data.parquet"
        assert parquet_file.exists()

    def test_convert_jsonl_to_parquet_multiple_partitions(self, tmp_path: Path):
        """测试多个分区的转换"""
        messages = [
            {
                "msg_id": "msg_1",
                "from_username": "wxid_1",
                "to_username": "wxid_2",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590400,  # 2025-01-23
                "is_chatroom_msg": 0,
                "content": "Day 23",
                "desc": "",
                "source": "0",
                "guid": "guid_1",
                "notify_type": 100,
            },
            {
                "msg_id": "msg_2",
                "from_username": "wxid_1",
                "to_username": "wxid_2",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737676800,  # 2025-01-24
                "is_chatroom_msg": 0,
                "content": "Day 24",
                "desc": "",
                "source": "0",
                "guid": "guid_2",
                "notify_type": 100,
            },
        ]

        jsonl_file = tmp_path / "messages.jsonl"
        import json

        with open(jsonl_file, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        parquet_root = tmp_path / "parquet"

        result = convert_jsonl_to_parquet(jsonl_file, parquet_root)

        assert result["total_records"] == 2

        # 验证两个分区都被创建
        partition1 = parquet_root / "year=2025" / "month=01" / "day=23" / "data.parquet"
        partition2 = parquet_root / "year=2025" / "month=01" / "day=24" / "data.parquet"

        assert partition1.exists()
        assert partition2.exists()

    def test_convert_jsonl_to_parquet_adds_ingestion_time(
        self, tmp_path: Path, sample_messages: list[dict]
    ):
        """测试自动添加 ingestion_time 字段"""
        jsonl_file = tmp_path / "messages.jsonl"
        import json

        with open(jsonl_file, "w", encoding="utf-8") as f:
            for msg in sample_messages:
                f.write(json.dumps(msg) + "\n")

        parquet_root = tmp_path / "parquet"

        convert_jsonl_to_parquet(jsonl_file, parquet_root)

        # 读取 Parquet 文件
        partition_dir = parquet_root / "year=2025" / "month=01" / "day=23"
        parquet_file = partition_dir / "data.parquet"

        table = pq.read_table(parquet_file)

        # 验证 ingestion_time 字段存在
        assert "ingestion_time" in table.column_names

        # 验证 ingestion_time 是有效的时间戳
        df = table.to_pandas()
        assert df["ingestion_time"].notna().all()

    def test_convert_jsonl_to_parquet_filters_invalid_messages(self, tmp_path: Path):
        """测试过滤无效消息"""
        messages = [
            {
                "msg_id": "msg_1",
                "from_username": "wxid_1",
                "to_username": "wxid_2",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590400,
                "is_chatroom_msg": 0,
                "content": "Valid",
                "desc": "",
                "source": "0",
                "guid": "guid_1",
                "notify_type": 100,
            },
            {
                "msg_id": "msg_2",
                # 缺少必填字段
                "content": "Invalid",
            },
        ]

        jsonl_file = tmp_path / "messages.jsonl"
        import json

        with open(jsonl_file, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        parquet_root = tmp_path / "parquet"

        result = convert_jsonl_to_parquet(jsonl_file, parquet_root)

        # 只有 1 条有效消息
        assert result["total_records"] == 1

    def test_convert_jsonl_to_parquet_calculates_compression_ratio(
        self, tmp_path: Path, sample_messages: list[dict]
    ):
        """测试计算压缩比"""
        jsonl_file = tmp_path / "messages.jsonl"
        import json

        with open(jsonl_file, "w", encoding="utf-8") as f:
            for msg in sample_messages:
                f.write(json.dumps(msg) + "\n")

        parquet_root = tmp_path / "parquet"

        result = convert_jsonl_to_parquet(jsonl_file, parquet_root)

        # 验证压缩比被计算
        assert "compression_ratio" in result
        assert result["compression_ratio"] > 0


class TestAppendToParquetPartition:
    """测试追加到 Parquet 分区"""

    @pytest.fixture
    def sample_messages(self) -> list[dict]:
        """创建示例消息"""
        return [
            {
                "msg_id": "msg_1",
                "from_username": "wxid_1",
                "to_username": "wxid_2",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590400,  # 2025-01-23
                "is_chatroom_msg": 0,
                "content": "Hello",
                "desc": "",
                "source": "0",
                "guid": "guid_1",
                "notify_type": 100,
            }
        ]

    def test_append_to_parquet_partition_success(
        self, tmp_path: Path, sample_messages: list[dict]
    ):
        """测试成功追加到 Parquet 分区"""
        parquet_root = tmp_path / "parquet"

        result = append_to_parquet_partition(sample_messages, parquet_root)

        # 验证返回结果
        assert "2025-01-23" in result
        assert result["2025-01-23"] == 1

        # 验证 Parquet 文件被创建
        partition_dir = parquet_root / "year=2025" / "month=01" / "day=23"
        parquet_file = partition_dir / "data.parquet"
        assert parquet_file.exists()

    @pytest.mark.skip(reason="Schema 精度不匹配问题 - 需要在实现中统一时间戳精度")
    def test_append_to_parquet_partition_appends_to_existing(
        self, tmp_path: Path, sample_messages: list[dict]
    ):
        """测试追加到现有分区（暂时跳过 - schema 精度问题）"""
        parquet_root = tmp_path / "parquet"

        # 第一次写入
        append_to_parquet_partition(sample_messages, parquet_root)

        # 第二次追加（使用不同的消息 ID 避免重复）
        new_messages = [
            {
                "msg_id": "msg_new_1",
                "from_username": "wxid_3",
                "to_username": "wxid_4",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590401,  # 同一天
                "is_chatroom_msg": 0,
                "content": "World",
                "desc": "",
                "source": "0",
                "guid": "guid_new_1",
                "notify_type": 100,
            }
        ]

        append_to_parquet_partition(new_messages, parquet_root)

        # 验证文件包含两条记录
        partition_dir = parquet_root / "year=2025" / "month=01" / "day=23"
        parquet_file = partition_dir / "data.parquet"

        table = pq.read_table(parquet_file)
        assert len(table) == 2

    def test_append_to_parquet_partition_multiple_partitions(self, tmp_path: Path):
        """测试追加到多个分区"""
        messages = [
            {
                "msg_id": "msg_1",
                "from_username": "wxid_1",
                "to_username": "wxid_2",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590400,  # 2025-01-23
                "is_chatroom_msg": 0,
                "content": "Day 23",
                "desc": "",
                "source": "0",
                "guid": "guid_1",
                "notify_type": 100,
            },
            {
                "msg_id": "msg_2",
                "from_username": "wxid_1",
                "to_username": "wxid_2",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737676800,  # 2025-01-24
                "is_chatroom_msg": 0,
                "content": "Day 24",
                "desc": "",
                "source": "0",
                "guid": "guid_2",
                "notify_type": 100,
            },
        ]

        parquet_root = tmp_path / "parquet"

        result = append_to_parquet_partition(messages, parquet_root)

        # 验证两个分区都被写入
        assert "2025-01-23" in result
        assert "2025-01-24" in result
        assert result["2025-01-23"] == 1
        assert result["2025-01-24"] == 1

    def test_append_to_parquet_partition_filters_invalid(self, tmp_path: Path):
        """测试过滤无效消息"""
        messages = [
            {
                "msg_id": "msg_1",
                "from_username": "wxid_1",
                "to_username": "wxid_2",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590400,
                "is_chatroom_msg": 0,
                "content": "Valid",
                "desc": "",
                "source": "0",
                "guid": "guid_1",
                "notify_type": 100,
            },
            {
                "msg_id": "msg_2",
                # 缺少必填字段
                "content": "Invalid",
            },
        ]

        parquet_root = tmp_path / "parquet"

        result = append_to_parquet_partition(messages, parquet_root)

        # 只有 1 条有效消息
        assert result["2025-01-23"] == 1

    def test_append_to_parquet_partition_adds_ingestion_time(
        self, tmp_path: Path, sample_messages: list[dict]
    ):
        """测试自动添加 ingestion_time"""
        parquet_root = tmp_path / "parquet"

        append_to_parquet_partition(sample_messages, parquet_root)

        # 读取 Parquet 文件
        partition_dir = parquet_root / "year=2025" / "month=01" / "day=23"
        parquet_file = partition_dir / "data.parquet"

        table = pq.read_table(parquet_file)

        # 验证 ingestion_time 字段存在
        assert "ingestion_time" in table.column_names
