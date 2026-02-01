"""存储管道集成测试

测试完整的存储管道：JSONL 写入 -> Parquet 转换 -> 数据验证
"""

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from diting.services.storage.ingestion import convert_jsonl_to_parquet
from diting.services.storage.jsonl_writer import JSONLWriter


class TestStoragePipelineIntegration:
    """测试完整的存储管道"""

    @pytest.fixture
    def storage_dirs(self, tmp_path: Path) -> dict[str, Path]:
        """创建存储目录"""
        return {
            "jsonl": tmp_path / "messages" / "raw",
            "parquet": tmp_path / "messages" / "parquet",
        }

    @pytest.fixture
    def sample_messages(self) -> list[dict]:
        """创建示例消息"""
        base_timestamp = 1737590400  # 2025-01-23 00:00:00 UTC

        return [
            {
                "msg_id": f"msg_{i}",
                "from_username": f"wxid_sender_{i}",
                "to_username": f"wxid_receiver_{i}",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": base_timestamp + i,
                "is_chatroom_msg": 0,
                "content": f"Message {i}",
                "desc": "",
                "source": "0",
                "guid": f"guid_{i}",
                "notify_type": 100,
            }
            for i in range(100)
        ]

    def test_end_to_end_storage_pipeline(
        self, storage_dirs: dict[str, Path], sample_messages: list[dict]
    ):
        """测试端到端存储管道"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        # 步骤 1: 写入 JSONL
        writer = JSONLWriter(base_dir=jsonl_dir)
        writer.append_batch(sample_messages)

        # 验证 JSONL 文件被创建
        jsonl_file = writer._get_current_file_path()
        assert jsonl_file.exists()

        # 步骤 2: 转换为 Parquet
        result = convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        # 验证转换结果
        assert result["total_records"] == 100
        assert result["source_size_mb"] > 0
        assert result["target_size_mb"] > 0
        assert result["compression_ratio"] > 0

        # 步骤 3: 验证 Parquet 数据
        partition_dir = parquet_dir / "year=2025" / "month=01" / "day=23"
        parquet_file = partition_dir / "data.parquet"
        assert parquet_file.exists()

        # 读取并验证数据
        table = pq.read_table(parquet_file)
        assert len(table) == 100

        # 验证字段
        assert "msg_id" in table.column_names
        assert "from_username" in table.column_names
        assert "create_time" in table.column_names
        assert "ingestion_time" in table.column_names

        # 验证数据内容
        df = table.to_pandas()
        assert df["msg_id"].iloc[0] == "msg_0"
        assert df["content"].iloc[0] == "Message 0"

    def test_incremental_storage_pipeline(
        self, storage_dirs: dict[str, Path], sample_messages: list[dict]
    ):
        """测试增量存储管道"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        writer = JSONLWriter(base_dir=jsonl_dir)

        # 第一批消息
        batch1 = sample_messages[:50]
        writer.append_batch(batch1)

        jsonl_file = writer._get_current_file_path()
        result1 = convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        assert result1["total_records"] == 50

        # 第二批消息（追加到同一个 JSONL 文件）
        batch2 = sample_messages[50:]
        writer.append_batch(batch2)

        # 重新转换（会覆盖之前的 Parquet 文件）
        result2 = convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        assert result2["total_records"] == 100

        # 验证最终数据
        partition_dir = parquet_dir / "year=2025" / "month=01" / "day=23"
        parquet_file = partition_dir / "data.parquet"

        table = pq.read_table(parquet_file)
        assert len(table) == 100

    def test_multi_day_storage_pipeline(self, storage_dirs: dict[str, Path]):
        """测试多天数据的存储管道"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        # 创建跨越 3 天的消息
        messages = []
        for day in range(3):
            base_timestamp = 1737590400 + (day * 86400)  # 每天 86400 秒
            for i in range(10):
                messages.append(
                    {
                        "msg_id": f"msg_day{day}_{i}",
                        "from_username": f"wxid_{i}",
                        "to_username": "wxid_receiver",
                        "chatroom": "",
                        "chatroom_sender": "",
                        "msg_type": 1,
                        "create_time": base_timestamp + i,
                        "is_chatroom_msg": 0,
                        "content": f"Day {day} Message {i}",
                        "desc": "",
                        "source": "0",
                        "guid": f"guid_day{day}_{i}",
                        "notify_type": 100,
                    }
                )

        # 写入 JSONL
        writer = JSONLWriter(base_dir=jsonl_dir)
        writer.append_batch(messages)

        # 转换为 Parquet
        jsonl_file = writer._get_current_file_path()
        result = convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        assert result["total_records"] == 30

        # 验证 3 个分区都被创建
        for day in range(3):
            day_num = 23 + day
            partition_dir = parquet_dir / "year=2025" / "month=01" / f"day={day_num:02d}"
            parquet_file = partition_dir / "data.parquet"
            assert parquet_file.exists()

            # 验证每个分区有 10 条记录
            table = pq.read_table(parquet_file)
            assert len(table) == 10

    def test_storage_pipeline_with_invalid_messages(
        self, storage_dirs: dict[str, Path], sample_messages: list[dict]
    ):
        """测试包含无效消息的存储管道"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        # 添加一些无效消息
        invalid_messages = [
            {"msg_id": "invalid_1"},  # 缺少必填字段
            {"msg_id": "invalid_2", "content": "No timestamp"},
        ]

        all_messages = sample_messages + invalid_messages

        # 写入 JSONL（包括无效消息）
        writer = JSONLWriter(base_dir=jsonl_dir)
        writer.append_batch(all_messages)

        # 转换为 Parquet（应该过滤掉无效消息）
        jsonl_file = writer._get_current_file_path()
        result = convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        # 只有有效消息被转换
        assert result["total_records"] == 100

    def test_storage_pipeline_compression_ratio(
        self, storage_dirs: dict[str, Path], sample_messages: list[dict]
    ):
        """测试存储管道的压缩比"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        writer = JSONLWriter(base_dir=jsonl_dir)
        writer.append_batch(sample_messages)

        jsonl_file = writer._get_current_file_path()
        result = convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        # 验证压缩比 > 1（Parquet 应该比 JSONL 小）
        assert result["compression_ratio"] > 1.0

        # 验证文件大小
        assert result["source_size_mb"] > result["target_size_mb"]

    def test_storage_pipeline_preserves_data_integrity(
        self, storage_dirs: dict[str, Path], sample_messages: list[dict]
    ):
        """测试存储管道保持数据完整性"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        writer = JSONLWriter(base_dir=jsonl_dir)
        writer.append_batch(sample_messages)

        jsonl_file = writer._get_current_file_path()
        convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        # 读取 Parquet 数据
        partition_dir = parquet_dir / "year=2025" / "month=01" / "day=23"
        parquet_file = partition_dir / "data.parquet"
        table = pq.read_table(parquet_file)
        df = table.to_pandas()

        # 验证所有原始消息的数据都存在
        for _i, original_msg in enumerate(sample_messages):
            row = df[df["msg_id"] == original_msg["msg_id"]].iloc[0]

            assert row["from_username"] == original_msg["from_username"]
            assert row["to_username"] == original_msg["to_username"]
            assert row["content"] == original_msg["content"]
            assert row["msg_type"] == original_msg["msg_type"]

    def test_storage_pipeline_with_unicode_content(self, storage_dirs: dict[str, Path]):
        """测试包含 Unicode 内容的存储管道"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        messages = [
            {
                "msg_id": "msg_unicode",
                "from_username": "wxid_sender",
                "to_username": "wxid_receiver",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590400,
                "is_chatroom_msg": 0,
                "content": "你好世界 🌍 Hello World",
                "desc": "测试描述",
                "source": "0",
                "guid": "guid_unicode",
                "notify_type": 100,
            }
        ]

        writer = JSONLWriter(base_dir=jsonl_dir)
        writer.append_batch(messages)

        jsonl_file = writer._get_current_file_path()
        convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        # 验证 Unicode 内容被正确保存
        partition_dir = parquet_dir / "year=2025" / "month=01" / "day=23"
        parquet_file = partition_dir / "data.parquet"
        table = pq.read_table(parquet_file)
        df = table.to_pandas()

        assert df["content"].iloc[0] == "你好世界 🌍 Hello World"
        assert df["desc"].iloc[0] == "测试描述"


class TestStoragePipelineErrorHandling:
    """测试存储管道的错误处理"""

    @pytest.fixture
    def storage_dirs(self, tmp_path: Path) -> dict[str, Path]:
        """创建存储目录"""
        return {
            "jsonl": tmp_path / "messages" / "raw",
            "parquet": tmp_path / "messages" / "parquet",
        }

    def test_convert_nonexistent_jsonl_file(self, storage_dirs: dict[str, Path]):
        """测试转换不存在的 JSONL 文件"""
        jsonl_file = storage_dirs["jsonl"] / "nonexistent.jsonl"
        parquet_dir = storage_dirs["parquet"]

        with pytest.raises(FileNotFoundError):
            convert_jsonl_to_parquet(jsonl_file, parquet_dir)

    def test_convert_empty_jsonl_file(self, storage_dirs: dict[str, Path]):
        """测试转换空 JSONL 文件"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        # 创建空 JSONL 文件
        jsonl_dir.mkdir(parents=True, exist_ok=True)
        jsonl_file = jsonl_dir / "empty.jsonl"
        jsonl_file.touch()

        result = convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        assert result["total_records"] == 0

    def test_convert_malformed_jsonl_file(self, storage_dirs: dict[str, Path]):
        """测试转换格式错误的 JSONL 文件"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        # 创建包含无效 JSON 的文件
        jsonl_dir.mkdir(parents=True, exist_ok=True)
        jsonl_file = jsonl_dir / "malformed.jsonl"

        with open(jsonl_file, "w", encoding="utf-8") as f:
            f.write('{"msg_id": "valid"}\n')
            f.write("invalid json line\n")  # 无效行
            f.write('{"msg_id": "valid2"}\n')

        # 应该跳过无效行并继续处理
        result = convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        # 只有有效的行被处理（但可能因为缺少必填字段而被过滤）
        # 这里主要验证不会抛出异常
        assert result is not None


class TestStoragePipelineConcurrency:
    """测试存储管道的并发性"""

    @pytest.fixture
    def storage_dirs(self, tmp_path: Path) -> dict[str, Path]:
        """创建存储目录"""
        return {
            "jsonl": tmp_path / "messages" / "raw",
            "parquet": tmp_path / "messages" / "parquet",
        }

    def test_concurrent_jsonl_writes(self, storage_dirs: dict[str, Path]):
        """测试并发 JSONL 写入"""
        import threading

        jsonl_dir = storage_dirs["jsonl"]
        writer = JSONLWriter(base_dir=jsonl_dir)

        def write_batch(start_id: int, count: int):
            messages = [
                {
                    "msg_id": f"msg_{start_id + i}",
                    "from_username": f"wxid_{i}",
                    "to_username": "wxid_receiver",
                    "chatroom": "",
                    "chatroom_sender": "",
                    "msg_type": 1,
                    "create_time": 1737590400 + i,
                    "is_chatroom_msg": 0,
                    "content": f"Message {i}",
                    "desc": "",
                    "source": "0",
                    "guid": f"guid_{i}",
                    "notify_type": 100,
                }
                for i in range(count)
            ]
            writer.append_batch(messages)

        # 创建多个线程并发写入
        threads = []
        for i in range(5):
            thread = threading.Thread(target=write_batch, args=(i * 20, 20))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有消息都被写入
        jsonl_file = writer._get_current_file_path()
        with open(jsonl_file, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 100

        # 验证所有消息 ID 唯一
        msg_ids = set()
        for line in lines:
            msg = json.loads(line)
            msg_ids.add(msg["msg_id"])

        assert len(msg_ids) == 100
