"""性能测试

验证存储管道满足性能契约：5分钟内处理 23,210 条消息
"""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from src.services.storage.ingestion import convert_jsonl_to_parquet
from src.services.storage.jsonl_writer import JSONLWriter


class TestStoragePerformance:
    """测试存储性能"""

    @pytest.fixture
    def storage_dirs(self, tmp_path: Path) -> dict[str, Path]:
        """创建存储目录"""
        return {
            "jsonl": tmp_path / "messages" / "raw",
            "parquet": tmp_path / "messages" / "parquet",
        }

    @pytest.fixture
    def large_message_dataset(self) -> list[dict]:
        """创建大规模消息数据集（23,210 条）"""
        messages = []
        base_timestamp = 1737590400  # 2025-01-23 00:00:00 UTC

        # 生成 23,210 条消息，分布在 30 天
        for i in range(23210):
            day_offset = (i % 30) * 86400  # 分布在 30 天
            messages.append(
                {
                    "msg_id": f"msg_{i:06d}",
                    "from_username": f"wxid_sender_{i % 100}",
                    "to_username": f"wxid_receiver_{i % 50}",
                    "chatroom": f"chatroom_{i % 20}" if i % 3 == 0 else "",
                    "chatroom_sender": f"wxid_member_{i % 30}" if i % 3 == 0 else "",
                    "msg_type": (i % 10) + 1,
                    "create_time": base_timestamp + day_offset + (i % 86400),
                    "is_chatroom_msg": 1 if i % 3 == 0 else 0,
                    "content": f"Message content {i} with some text to simulate real data",
                    "desc": f"Description {i}" if i % 5 == 0 else "",
                    "source": str(i % 3),
                    "guid": f"guid_{i:06d}",
                    "notify_type": 100 + (i % 5),
                }
            )

        return messages

    @pytest.mark.slow
    def test_process_23210_messages_under_5_minutes(
        self, storage_dirs: dict[str, Path], large_message_dataset: list[dict]
    ):
        """测试 5 分钟内处理 23,210 条消息（SC-001 性能契约）"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        start_time = time.time()

        # 步骤 1: 写入 JSONL
        writer = JSONLWriter(base_dir=jsonl_dir)
        writer.append_batch(large_message_dataset)

        jsonl_write_time = time.time() - start_time
        print(f"\nJSONL 写入时间: {jsonl_write_time:.2f} 秒")

        # 步骤 2: 转换为 Parquet
        jsonl_file = writer._get_current_file_path()
        conversion_start = time.time()

        result = convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        conversion_time = time.time() - conversion_start
        print(f"Parquet 转换时间: {conversion_time:.2f} 秒")

        total_time = time.time() - start_time
        print(f"总处理时间: {total_time:.2f} 秒")
        print(f"处理速度: {len(large_message_dataset) / total_time:.2f} 条/秒")

        # 性能契约: 5 分钟 = 300 秒
        assert total_time < 300, f"处理时间超过 5 分钟: {total_time:.2f} 秒"

        # 验证所有消息都被处理
        assert result["total_records"] == 23210

        # 验证压缩比
        print(f"源文件大小: {result['source_size_mb']:.2f} MB")
        print(f"目标文件大小: {result['target_size_mb']:.2f} MB")
        print(f"压缩比: {result['compression_ratio']:.2f}x")

    @pytest.mark.slow
    def test_jsonl_write_performance(
        self, storage_dirs: dict[str, Path], large_message_dataset: list[dict]
    ):
        """测试 JSONL 写入性能"""
        jsonl_dir = storage_dirs["jsonl"]
        writer = JSONLWriter(base_dir=jsonl_dir)

        start_time = time.time()
        writer.append_batch(large_message_dataset)
        elapsed_time = time.time() - start_time

        print(f"\nJSONL 写入性能:")
        print(f"  消息数量: {len(large_message_dataset)}")
        print(f"  总时间: {elapsed_time:.2f} 秒")
        print(f"  吞吐量: {len(large_message_dataset) / elapsed_time:.2f} 条/秒")

        # JSONL 写入应该很快（< 30 秒）
        assert elapsed_time < 30, f"JSONL 写入时间过长: {elapsed_time:.2f} 秒"

    @pytest.mark.slow
    def test_parquet_conversion_performance(
        self, storage_dirs: dict[str, Path], large_message_dataset: list[dict]
    ):
        """测试 Parquet 转换性能"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        # 先写入 JSONL
        writer = JSONLWriter(base_dir=jsonl_dir)
        writer.append_batch(large_message_dataset)

        jsonl_file = writer._get_current_file_path()

        # 测试转换性能
        start_time = time.time()
        result = convert_jsonl_to_parquet(jsonl_file, parquet_dir)
        elapsed_time = time.time() - start_time

        print(f"\nParquet 转换性能:")
        print(f"  消息数量: {result['total_records']}")
        print(f"  总时间: {elapsed_time:.2f} 秒")
        print(f"  吞吐量: {result['total_records'] / elapsed_time:.2f} 条/秒")

        # Parquet 转换应该在合理时间内完成（< 5 分钟）
        assert elapsed_time < 300, f"Parquet 转换时间过长: {elapsed_time:.2f} 秒"

    def test_single_message_write_latency(self, storage_dirs: dict[str, Path]):
        """测试单条消息写入延迟"""
        jsonl_dir = storage_dirs["jsonl"]
        writer = JSONLWriter(base_dir=jsonl_dir)

        message = {
            "msg_id": "test_latency",
            "from_username": "wxid_sender",
            "to_username": "wxid_receiver",
            "chatroom": "",
            "chatroom_sender": "",
            "msg_type": 1,
            "create_time": 1737590400,
            "is_chatroom_msg": 0,
            "content": "Test message",
            "desc": "",
            "source": "0",
            "guid": "guid_test",
            "notify_type": 100,
        }

        # 测试多次写入的平均延迟
        latencies = []
        for _ in range(100):
            start_time = time.time()
            writer.append_message(message)
            latency = time.time() - start_time
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"\n单条消息写入延迟:")
        print(f"  平均延迟: {avg_latency * 1000:.2f} ms")
        print(f"  最大延迟: {max_latency * 1000:.2f} ms")

        # 平均延迟应该 < 10ms
        assert avg_latency < 0.01, f"平均延迟过高: {avg_latency * 1000:.2f} ms"

    def test_batch_write_throughput(self, storage_dirs: dict[str, Path]):
        """测试批量写入吞吐量"""
        jsonl_dir = storage_dirs["jsonl"]
        writer = JSONLWriter(base_dir=jsonl_dir)

        # 创建 1000 条消息
        messages = [
            {
                "msg_id": f"msg_{i}",
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
            for i in range(1000)
        ]

        start_time = time.time()
        writer.append_batch(messages)
        elapsed_time = time.time() - start_time

        throughput = len(messages) / elapsed_time

        print(f"\n批量写入吞吐量:")
        print(f"  消息数量: {len(messages)}")
        print(f"  总时间: {elapsed_time:.2f} 秒")
        print(f"  吞吐量: {throughput:.2f} 条/秒")

        # 批量写入吞吐量应该 > 1000 条/秒
        assert throughput > 1000, f"吞吐量过低: {throughput:.2f} 条/秒"

    @pytest.mark.slow
    def test_multi_partition_conversion_performance(self, storage_dirs: dict[str, Path]):
        """测试多分区转换性能"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        # 创建跨越 30 天的消息
        messages = []
        base_timestamp = 1737590400

        for day in range(30):
            day_timestamp = base_timestamp + (day * 86400)
            for i in range(100):  # 每天 100 条消息
                messages.append(
                    {
                        "msg_id": f"msg_day{day}_{i}",
                        "from_username": f"wxid_{i}",
                        "to_username": "wxid_receiver",
                        "chatroom": "",
                        "chatroom_sender": "",
                        "msg_type": 1,
                        "create_time": day_timestamp + i,
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

        # 测试转换性能
        jsonl_file = writer._get_current_file_path()
        start_time = time.time()
        result = convert_jsonl_to_parquet(jsonl_file, parquet_dir)
        elapsed_time = time.time() - start_time

        print(f"\n多分区转换性能:")
        print(f"  消息数量: {result['total_records']}")
        print(f"  分区数量: 30")
        print(f"  总时间: {elapsed_time:.2f} 秒")
        print(f"  吞吐量: {result['total_records'] / elapsed_time:.2f} 条/秒")

        # 多分区转换应该在合理时间内完成
        assert elapsed_time < 60, f"多分区转换时间过长: {elapsed_time:.2f} 秒"

    def test_compression_efficiency(
        self, storage_dirs: dict[str, Path], large_message_dataset: list[dict]
    ):
        """测试压缩效率"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        # 写入 JSONL
        writer = JSONLWriter(base_dir=jsonl_dir)
        writer.append_batch(large_message_dataset)

        # 转换为 Parquet
        jsonl_file = writer._get_current_file_path()
        result = convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        print(f"\n压缩效率:")
        print(f"  源文件大小: {result['source_size_mb']:.2f} MB")
        print(f"  目标文件大小: {result['target_size_mb']:.2f} MB")
        print(f"  压缩比: {result['compression_ratio']:.2f}x")
        print(f"  空间节省: {(1 - 1/result['compression_ratio']) * 100:.1f}%")

        # Parquet 应该比 JSONL 小（压缩比 > 1）
        assert result["compression_ratio"] > 1.0, "Parquet 文件应该比 JSONL 小"

        # 合理的压缩比应该 > 2x
        assert result["compression_ratio"] > 2.0, f"压缩比过低: {result['compression_ratio']:.2f}x"


class TestStorageScalability:
    """测试存储可扩展性"""

    @pytest.fixture
    def storage_dirs(self, tmp_path: Path) -> dict[str, Path]:
        """创建存储目录"""
        return {
            "jsonl": tmp_path / "messages" / "raw",
            "parquet": tmp_path / "messages" / "parquet",
        }

    def test_memory_usage_large_dataset(
        self, storage_dirs: dict[str, Path], large_message_dataset: list[dict]
    ):
        """测试大数据集的内存使用"""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil 未安装，跳过内存测试")

        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        # 写入和转换
        writer = JSONLWriter(base_dir=jsonl_dir)
        writer.append_batch(large_message_dataset)

        jsonl_file = writer._get_current_file_path()
        convert_jsonl_to_parquet(jsonl_file, parquet_dir)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"\n内存使用:")
        print(f"  初始内存: {initial_memory:.2f} MB")
        print(f"  最终内存: {final_memory:.2f} MB")
        print(f"  内存增长: {memory_increase:.2f} MB")

        # 内存增长应该合理（< 500 MB）
        assert memory_increase < 500, f"内存增长过大: {memory_increase:.2f} MB"

    def test_disk_io_efficiency(self, storage_dirs: dict[str, Path]):
        """测试磁盘 I/O 效率"""
        jsonl_dir = storage_dirs["jsonl"]
        parquet_dir = storage_dirs["parquet"]

        # 创建 10000 条消息
        messages = [
            {
                "msg_id": f"msg_{i}",
                "from_username": f"wxid_{i}",
                "to_username": "wxid_receiver",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590400 + i,
                "is_chatroom_msg": 0,
                "content": f"Message {i} with some content",
                "desc": "",
                "source": "0",
                "guid": f"guid_{i}",
                "notify_type": 100,
            }
            for i in range(10000)
        ]

        # 写入 JSONL
        writer = JSONLWriter(base_dir=jsonl_dir)
        start_time = time.time()
        writer.append_batch(messages)
        write_time = time.time() - start_time

        # 转换为 Parquet
        jsonl_file = writer._get_current_file_path()
        start_time = time.time()
        convert_jsonl_to_parquet(jsonl_file, parquet_dir)
        conversion_time = time.time() - start_time

        print(f"\n磁盘 I/O 效率:")
        print(f"  JSONL 写入时间: {write_time:.2f} 秒")
        print(f"  Parquet 转换时间: {conversion_time:.2f} 秒")
        print(f"  总时间: {write_time + conversion_time:.2f} 秒")

        # 总时间应该合理（< 60 秒）
        assert (write_time + conversion_time) < 60, "磁盘 I/O 时间过长"


@pytest.fixture(scope="session")
def large_message_dataset() -> list[dict]:
    """会话级别的大数据集 fixture（避免重复生成）"""
    messages = []
    base_timestamp = 1737590400

    for i in range(23210):
        day_offset = (i % 30) * 86400
        messages.append(
            {
                "msg_id": f"msg_{i:06d}",
                "from_username": f"wxid_sender_{i % 100}",
                "to_username": f"wxid_receiver_{i % 50}",
                "chatroom": f"chatroom_{i % 20}" if i % 3 == 0 else "",
                "chatroom_sender": f"wxid_member_{i % 30}" if i % 3 == 0 else "",
                "msg_type": (i % 10) + 1,
                "create_time": base_timestamp + day_offset + (i % 86400),
                "is_chatroom_msg": 1 if i % 3 == 0 else 0,
                "content": f"Message content {i} with some text to simulate real data",
                "desc": f"Description {i}" if i % 5 == 0 else "",
                "source": str(i % 3),
                "guid": f"guid_{i:06d}",
                "notify_type": 100 + (i % 5),
            }
        )

    return messages
