"""ParquetWriter 单元测试"""

import pyarrow.parquet as pq
import pytest
from diting.services.storage.parquet_writer import ParquetWriter


def create_test_message(msg_id: str, create_time: int, content: str = "Hello") -> dict:
    """创建测试消息，包含所有必需字段"""
    return {
        "msg_id": msg_id,
        "from_username": "user1",
        "to_username": "user2",
        "chatroom": "",
        "chatroom_sender": "",
        "msg_type": 1,
        "create_time": create_time,
        "is_chatroom_msg": 0,
        "content": content,
        "desc": "",
        "source": "",
        "guid": "test-guid",
        "notify_type": 1010,
    }


class TestParquetWriterInit:
    """ParquetWriter 初始化测试"""

    def test_initializes_with_defaults(self, tmp_path):
        """测试默认初始化"""
        writer = ParquetWriter(tmp_path)
        assert writer.parquet_root == tmp_path
        assert writer.compression == "snappy"
        assert writer.schema is not None

    def test_initializes_with_custom_compression(self, tmp_path):
        """测试自定义压缩算法"""
        writer = ParquetWriter(tmp_path, compression="gzip")
        assert writer.compression == "gzip"


class TestWritePartition:
    """write_partition 方法测试"""

    def test_writes_partition_successfully(self, tmp_path):
        """测试成功写入分区"""
        writer = ParquetWriter(tmp_path)
        messages = [create_test_message("msg-001", 1704067200)]

        parquet_file, count = writer.write_partition(messages, "2024-01-01")

        assert count == 1
        assert parquet_file.exists()

        # 验证文件内容
        table = pq.read_table(parquet_file)
        df = table.to_pandas()
        assert len(df) == 1
        assert df.iloc[0]["msg_id"] == "msg-001"

    def test_adds_ingestion_time(self, tmp_path):
        """测试添加摄入时间"""
        writer = ParquetWriter(tmp_path)
        messages = [create_test_message("msg-001", 1704067200)]

        parquet_file, _ = writer.write_partition(messages, "2024-01-01")

        table = pq.read_table(parquet_file)
        df = table.to_pandas()
        assert "ingestion_time" in df.columns
        assert df.iloc[0]["ingestion_time"] is not None

    def test_raises_error_for_empty_messages(self, tmp_path):
        """测试空消息列表抛出错误"""
        writer = ParquetWriter(tmp_path)

        with pytest.raises(ValueError, match="cannot be empty"):
            writer.write_partition([], "2024-01-01")

    def test_append_mode_combines_data(self, tmp_path):
        """测试追加模式合并数据"""
        writer = ParquetWriter(tmp_path)

        # 第一次写入
        messages1 = [create_test_message("msg-001", 1704067200, "First")]
        parquet_file, _ = writer.write_partition(messages1, "2024-01-01")

        # 第二次追加
        messages2 = [create_test_message("msg-002", 1704067200, "Second")]
        writer.write_partition(messages2, "2024-01-01", append=True)

        # 验证合并结果
        table = pq.read_table(parquet_file)
        df = table.to_pandas()
        assert len(df) == 2
        assert set(df["msg_id"]) == {"msg-001", "msg-002"}


class TestWritePartitions:
    """write_partitions 方法测试"""

    def test_writes_multiple_partitions(self, tmp_path):
        """测试写入多个分区"""
        writer = ParquetWriter(tmp_path)
        partitions = {
            "2024-01-01": [create_test_message("msg-001", 1704067200, "Day 1")],
            "2024-01-02": [create_test_message("msg-002", 1704153600, "Day 2")],
        }

        counts = writer.write_partitions(partitions)

        assert counts["2024-01-01"] == 1
        assert counts["2024-01-02"] == 1

    def test_returns_empty_for_empty_partitions(self, tmp_path):
        """测试空分区返回空字典"""
        writer = ParquetWriter(tmp_path)
        counts = writer.write_partitions({})

        assert counts == {}
