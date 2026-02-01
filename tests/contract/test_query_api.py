"""
契约测试: 查询 API

验证查询服务的 API 契约符合 contracts/storage-api.md 规范。
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest


class TestQueryMessagesContract:
    """query_messages API 契约测试"""

    @pytest.fixture
    def sample_parquet_data(self, tmp_path: Path):
        """创建测试用的 Parquet 数据集"""
        # 创建测试消息数据
        messages = [
            {
                "msg_id": f"msg_{i}",
                "from_username": f"user_{i % 5}",
                "to_username": "filehelper",
                "chatroom": "chatroom_123" if i % 3 == 0 else "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1769126400 + i * 3600,  # 2026-01-23 00:00:00 + 每小时一条
                "is_chatroom_msg": 1 if i % 3 == 0 else 0,
                "content": f"Message {i}",
                "desc": "",
                "source": "0",
                "guid": f"guid_{i}",
                "notify_type": 100,
            }
            for i in range(100)
        ]

        # 添加分区字段
        for msg in messages:
            dt = datetime.fromtimestamp(msg["create_time"])
            msg["year"] = dt.year
            msg["month"] = dt.month
            msg["day"] = dt.day

        # 写入 Parquet 分区数据集
        parquet_root = tmp_path / "parquet" / "messages"
        table = pa.Table.from_pylist(messages)
        pq.write_to_dataset(
            table,
            root_path=str(parquet_root),
            partition_cols=["year", "month", "day"],
            compression="snappy",
        )

        return parquet_root

    def test_query_messages_signature(self, sample_parquet_data: Path):
        """测试 query_messages 函数签名"""
        from diting.services.storage.query import query_messages

        # 验证函数存在
        assert callable(query_messages)

        # 验证参数签名
        import inspect

        sig = inspect.signature(query_messages)
        params = sig.parameters

        assert "start_date" in params
        assert "end_date" in params
        assert "parquet_root" in params
        assert "filters" in params
        assert "columns" in params

        # 验证默认值
        assert params["parquet_root"].default != inspect.Parameter.empty
        assert params["filters"].default is None
        assert params["columns"].default is None

    def test_query_messages_returns_dataframe(self, sample_parquet_data: Path):
        """测试 query_messages 返回 DataFrame"""
        from diting.services.storage.query import query_messages

        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-23",
            parquet_root=str(sample_parquet_data),
        )

        # 验证返回类型
        assert isinstance(result, pd.DataFrame)

    def test_query_messages_with_date_range(self, sample_parquet_data: Path):
        """测试日期范围查询"""
        from diting.services.storage.query import query_messages

        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-23",
            parquet_root=str(sample_parquet_data),
        )

        # 验证返回数据
        assert len(result) > 0
        assert "msg_id" in result.columns
        assert "from_username" in result.columns
        assert "content" in result.columns

    def test_query_messages_with_filters(self, sample_parquet_data: Path):
        """测试带过滤条件的查询"""
        from diting.services.storage.query import query_messages

        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-23",
            parquet_root=str(sample_parquet_data),
            filters={"chatroom": "chatroom_123"},
        )

        # 验证过滤结果
        assert len(result) > 0
        assert all(result["chatroom"] == "chatroom_123")

    def test_query_messages_with_columns(self, sample_parquet_data: Path):
        """测试列裁剪"""
        from diting.services.storage.query import query_messages

        result = query_messages(
            start_date="2026-01-23",
            end_date="2026-01-23",
            parquet_root=str(sample_parquet_data),
            columns=["msg_id", "content"],
        )

        # 验证返回的列
        assert len(result.columns) == 2
        assert "msg_id" in result.columns
        assert "content" in result.columns

    def test_query_messages_empty_result(self, sample_parquet_data: Path):
        """测试空结果查询"""
        from diting.services.storage.query import query_messages

        result = query_messages(
            start_date="2025-01-01",
            end_date="2025-01-01",
            parquet_root=str(sample_parquet_data),
        )

        # 验证空结果
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_query_messages_invalid_date_format(self, sample_parquet_data: Path):
        """测试无效日期格式"""
        from diting.services.storage.query import query_messages

        with pytest.raises(ValueError):
            query_messages(
                start_date="invalid-date",
                end_date="2026-01-23",
                parquet_root=str(sample_parquet_data),
            )

    def test_query_messages_nonexistent_path(self):
        """测试不存在的路径"""
        from diting.services.storage.query import query_messages

        with pytest.raises(FileNotFoundError):
            query_messages(
                start_date="2026-01-23",
                end_date="2026-01-23",
                parquet_root="/nonexistent/path",
            )


class TestQueryMessagesByIdContract:
    """query_messages_by_id API 契约测试"""

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
                "create_time": 1769126400 + i * 3600,  # 2026-01-23 00:00:00 + 每小时一条
                "is_chatroom_msg": 0,
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

    def test_query_messages_by_id_signature(self, sample_parquet_data: Path):
        """测试 query_messages_by_id 函数签名"""
        from diting.services.storage.query import query_messages_by_id

        # 验证函数存在
        assert callable(query_messages_by_id)

        # 验证参数签名
        import inspect

        sig = inspect.signature(query_messages_by_id)
        params = sig.parameters

        assert "msg_ids" in params
        assert "parquet_root" in params
        assert "columns" in params

    def test_query_messages_by_id_single_id(self, sample_parquet_data: Path):
        """测试单个 ID 查询"""
        from diting.services.storage.query import query_messages_by_id

        result = query_messages_by_id(
            msg_ids=["msg_0"],
            parquet_root=str(sample_parquet_data),
        )

        # 验证返回结果
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["msg_id"] == "msg_0"

    def test_query_messages_by_id_multiple_ids(self, sample_parquet_data: Path):
        """测试多个 ID 查询"""
        from diting.services.storage.query import query_messages_by_id

        result = query_messages_by_id(
            msg_ids=["msg_0", "msg_5", "msg_10"],
            parquet_root=str(sample_parquet_data),
        )

        # 验证返回结果
        assert len(result) == 3
        assert set(result["msg_id"]) == {"msg_0", "msg_5", "msg_10"}

    def test_query_messages_by_id_nonexistent_id(self, sample_parquet_data: Path):
        """测试不存在的 ID"""
        from diting.services.storage.query import query_messages_by_id

        result = query_messages_by_id(
            msg_ids=["nonexistent_id"],
            parquet_root=str(sample_parquet_data),
        )

        # 验证空结果
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_query_messages_by_id_with_columns(self, sample_parquet_data: Path):
        """测试列裁剪"""
        from diting.services.storage.query import query_messages_by_id

        result = query_messages_by_id(
            msg_ids=["msg_0"],
            parquet_root=str(sample_parquet_data),
            columns=["msg_id", "content"],
        )

        # 验证返回的列
        assert len(result.columns) == 2
        assert "msg_id" in result.columns
        assert "content" in result.columns
