"""
集成测试: 多条件过滤查询

验证查询服务的多条件过滤功能。
"""

from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.services.storage.query import query_messages, query_messages_by_id


class TestQueryFilters:
    """多条件过滤集成测试"""

    @pytest.fixture
    def sample_dataset(self, tmp_path: Path):
        """创建测试数据集"""
        parquet_root = tmp_path / "parquet" / "messages"

        # 生成多样化的测试数据
        messages = []
        base_timestamp = int(datetime(2026, 1, 23).timestamp())

        for i in range(200):
            timestamp = base_timestamp + i * 3600
            dt = datetime.fromtimestamp(timestamp)

            messages.append(
                {
                    "msg_id": f"msg_{i}",
                    "from_username": f"user_{i % 10}",  # 10 个不同用户
                    "to_username": "filehelper",
                    "chatroom": f"chatroom_{i % 5}" if i % 2 == 0 else "",  # 5 个群聊
                    "chatroom_sender": f"sender_{i % 8}" if i % 2 == 0 else "",
                    "msg_type": (i % 4) + 1,  # 4 种消息类型
                    "create_time": timestamp,
                    "is_chatroom_msg": 1 if i % 2 == 0 else 0,
                    "content": f"Message {i}",
                    "desc": "",
                    "source": "0",
                    "guid": f"guid_{i}",
                    "notify_type": 100,
                    "year": dt.year,
                    "month": dt.month,
                    "day": dt.day,
                }
            )

        # 写入 Parquet
        table = pa.Table.from_pylist(messages)
        pq.write_to_dataset(
            table,
            root_path=str(parquet_root),
            partition_cols=["year", "month", "day"],
            compression="snappy",
        )

        return parquet_root

    def test_filter_by_chatroom(self, sample_dataset: Path):
        """测试按群聊过滤"""
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-31",
            parquet_root=str(sample_dataset),
            filters={"chatroom": "chatroom_0"},
        )

        # 验证所有结果都属于指定群聊
        assert len(result) > 0
        assert all(result["chatroom"] == "chatroom_0")

    def test_filter_by_from_username(self, sample_dataset: Path):
        """测试按发送者过滤"""
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-31",
            parquet_root=str(sample_dataset),
            filters={"from_username": "user_5"},
        )

        # 验证所有结果都来自指定用户
        assert len(result) > 0
        assert all(result["from_username"] == "user_5")

    def test_filter_by_msg_type(self, sample_dataset: Path):
        """测试按消息类型过滤"""
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-31",
            parquet_root=str(sample_dataset),
            filters={"msg_type": 1},
        )

        # 验证所有结果都是指定类型
        assert len(result) > 0
        assert all(result["msg_type"] == 1)

    def test_filter_multiple_conditions(self, sample_dataset: Path):
        """测试多条件组合过滤"""
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-31",
            parquet_root=str(sample_dataset),
            filters={
                "chatroom": "chatroom_0",
                "msg_type": 1,
            },
        )

        # 验证所有结果都满足所有条件
        assert len(result) > 0
        assert all(result["chatroom"] == "chatroom_0")
        assert all(result["msg_type"] == 1)

    def test_filter_with_empty_result(self, sample_dataset: Path):
        """测试过滤条件导致空结果"""
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-31",
            parquet_root=str(sample_dataset),
            filters={"chatroom": "nonexistent_chatroom"},
        )

        # 验证返回空结果
        assert len(result) == 0

    def test_filter_with_column_projection(self, sample_dataset: Path):
        """测试过滤 + 列裁剪组合"""
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-31",
            parquet_root=str(sample_dataset),
            filters={"chatroom": "chatroom_0"},
            columns=["msg_id", "content", "chatroom"],
        )

        # 验证结果
        assert len(result) > 0
        assert "msg_id" in result.columns
        assert "content" in result.columns
        assert "chatroom" in result.columns
        assert all(result["chatroom"] == "chatroom_0")

    def test_query_by_id_multiple(self, sample_dataset: Path):
        """测试批量 ID 查询"""
        msg_ids = ["msg_0", "msg_10", "msg_20", "msg_30"]

        result = query_messages_by_id(
            msg_ids=msg_ids,
            parquet_root=str(sample_dataset),
        )

        # 验证返回所有请求的消息
        assert len(result) == len(msg_ids)
        assert set(result["msg_id"]) == set(msg_ids)

    def test_query_by_id_with_nonexistent(self, sample_dataset: Path):
        """测试 ID 查询包含不存在的 ID"""
        msg_ids = ["msg_0", "nonexistent_1", "msg_10", "nonexistent_2"]

        result = query_messages_by_id(
            msg_ids=msg_ids,
            parquet_root=str(sample_dataset),
        )

        # 验证只返回存在的消息
        assert len(result) == 2
        assert set(result["msg_id"]) == {"msg_0", "msg_10"}

    def test_complex_filter_scenario(self, sample_dataset: Path):
        """测试复杂过滤场景"""
        # 场景: 查询特定群聊中特定用户发送的特定类型消息
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-31",
            parquet_root=str(sample_dataset),
            filters={
                "chatroom": "chatroom_0",
                "from_username": "user_0",
                "msg_type": 1,
            },
            columns=["msg_id", "from_username", "chatroom", "msg_type", "content"],
        )

        # 验证所有条件都满足
        if len(result) > 0:
            assert all(result["chatroom"] == "chatroom_0")
            assert all(result["from_username"] == "user_0")
            assert all(result["msg_type"] == 1)

    def test_date_range_boundary(self, sample_dataset: Path):
        """测试日期范围边界"""
        # 查询精确的日期范围
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-23",
            parquet_root=str(sample_dataset),
        )

        # 验证所有消息都在指定日期
        assert len(result) > 0
        start_ts = int(datetime(2026, 1, 23).timestamp())
        end_ts = int(datetime(2026, 1, 23, 23, 59, 59).timestamp())
        assert all(result["create_time"] >= start_ts)
        assert all(result["create_time"] <= end_ts)
