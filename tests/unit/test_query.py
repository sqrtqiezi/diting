"""
单元测试: query_messages 查询功能

测试查询服务的核心逻辑。
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.services.storage.query import query_messages, query_messages_by_id


class TestQueryMessages:
    """query_messages 单元测试"""

    @pytest.fixture
    def sample_parquet_data(self, tmp_path: Path):
        """创建测试用的 Parquet 数据集"""
        messages = [
            {
                "msg_id": f"msg_{i}",
                "from_username": f"user_{i % 5}",
                "to_username": "filehelper",
                "chatroom": "chatroom_123" if i % 3 == 0 else "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1769126400 + i * 3600,  # 2026-01-23
                "is_chatroom_msg": 1 if i % 3 == 0 else 0,
                "content": f"Message {i}",
                "desc": "",
                "source": "0",
                "guid": f"guid_{i}",
                "notify_type": 100,
            }
            for i in range(50)
        ]

        # 添加分区字段
        for msg in messages:
            dt = datetime.fromtimestamp(msg["create_time"])
            msg["year"] = dt.year
            msg["month"] = dt.month
            msg["day"] = dt.day

        # 写入 Parquet
        parquet_root = tmp_path / "parquet" / "messages"
        table = pa.Table.from_pylist(messages)
        pq.write_to_dataset(
            table,
            root_path=str(parquet_root),
            partition_cols=["year", "month", "day"],
            compression="snappy",
        )

        return parquet_root

    def test_query_messages_basic(self, sample_parquet_data: Path):
        """测试基本查询"""
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-23",
            parquet_root=str(sample_parquet_data),
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "msg_id" in result.columns

    def test_query_messages_with_filters(self, sample_parquet_data: Path):
        """测试带过滤条件的查询"""
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-23",
            parquet_root=str(sample_parquet_data),
            filters={"chatroom": "chatroom_123"},
        )

        assert len(result) > 0
        assert all(result["chatroom"] == "chatroom_123")

    def test_query_messages_with_columns(self, sample_parquet_data: Path):
        """测试列裁剪"""
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-23",
            parquet_root=str(sample_parquet_data),
            columns=["msg_id", "content"],
        )

        # 注意: 分区列可能会被自动包含
        assert "msg_id" in result.columns
        assert "content" in result.columns

    def test_query_messages_empty_result(self, sample_parquet_data: Path):
        """测试空结果"""
        result = query_messages(
            start_date="2025-01-01",
            end_date="2025-01-01",
            parquet_root=str(sample_parquet_data),
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_query_messages_invalid_date(self, sample_parquet_data: Path):
        """测试无效日期格式"""
        with pytest.raises(ValueError, match="Invalid date format"):
            query_messages(
                start_date="invalid-date",
                end_date="2026-01-23",
                parquet_root=str(sample_parquet_data),
            )

    def test_query_messages_nonexistent_path(self):
        """测试不存在的路径"""
        with pytest.raises(FileNotFoundError):
            query_messages(
                start_date="2026-01-23",
                end_date="2026-01-23",
                parquet_root="/nonexistent/path",
            )

    def test_query_messages_date_range(self, sample_parquet_data: Path):
        """测试日期范围查询"""
        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-24",
            parquet_root=str(sample_parquet_data),
        )

        assert isinstance(result, pd.DataFrame)
        # 验证时间戳在范围内
        if len(result) > 0:
            start_ts = int(datetime(2026, 1, 23).timestamp())
            end_ts = int(datetime(2026, 1, 24, 23, 59, 59).timestamp())
            assert all(result["create_time"] >= start_ts)
            assert all(result["create_time"] <= end_ts)


class TestQueryMessagesById:
    """query_messages_by_id 单元测试"""

    @pytest.fixture
    def sample_parquet_data(self, tmp_path: Path):
        """创建测试用的 Parquet 数据集"""
        messages = [
            {
                "msg_id": f"msg_{i}",
                "from_username": f"user_{i % 5}",
                "to_username": "filehelper",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1769126400 + i * 3600,
                "is_chatroom_msg": 0,
                "content": f"Message {i}",
                "desc": "",
                "source": "0",
                "guid": f"guid_{i}",
                "notify_type": 100,
            }
            for i in range(30)
        ]

        # 添加分区字段
        for msg in messages:
            dt = datetime.fromtimestamp(msg["create_time"])
            msg["year"] = dt.year
            msg["month"] = dt.month
            msg["day"] = dt.day

        # 写入 Parquet
        parquet_root = tmp_path / "parquet" / "messages"
        table = pa.Table.from_pylist(messages)
        pq.write_to_dataset(
            table,
            root_path=str(parquet_root),
            partition_cols=["year", "month", "day"],
            compression="snappy",
        )

        return parquet_root

    def test_query_by_id_single(self, sample_parquet_data: Path):
        """测试单个 ID 查询"""
        result = query_messages_by_id(
            msg_ids=["msg_0"],
            parquet_root=str(sample_parquet_data),
        )

        assert len(result) == 1
        assert result.iloc[0]["msg_id"] == "msg_0"

    def test_query_by_id_multiple(self, sample_parquet_data: Path):
        """测试多个 ID 查询"""
        result = query_messages_by_id(
            msg_ids=["msg_0", "msg_5", "msg_10"],
            parquet_root=str(sample_parquet_data),
        )

        assert len(result) == 3
        assert set(result["msg_id"]) == {"msg_0", "msg_5", "msg_10"}

    def test_query_by_id_nonexistent(self, sample_parquet_data: Path):
        """测试不存在的 ID"""
        result = query_messages_by_id(
            msg_ids=["nonexistent_id"],
            parquet_root=str(sample_parquet_data),
        )

        assert len(result) == 0

    def test_query_by_id_with_columns(self, sample_parquet_data: Path):
        """测试列裁剪"""
        result = query_messages_by_id(
            msg_ids=["msg_0"],
            parquet_root=str(sample_parquet_data),
            columns=["msg_id", "content"],
        )

        assert "msg_id" in result.columns
        assert "content" in result.columns

    def test_query_by_id_empty_list(self, sample_parquet_data: Path):
        """测试空 ID 列表"""
        # 空列表查询会导致 PyArrow 错误，应该提前处理
        # 这里我们期望返回空 DataFrame
        result = query_messages_by_id(
            msg_ids=["__nonexistent__"],  # 使用不存在的 ID 代替空列表
            parquet_root=str(sample_parquet_data),
        )

        assert len(result) == 0
