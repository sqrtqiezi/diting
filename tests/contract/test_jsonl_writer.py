"""JSONL 写入器契约测试

验证 JSONLWriter API 的契约稳定性。
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from typing import Any

# 注意: 这些导入在实现之前会失败,这是 TDD 的预期行为
try:
    from src.services.storage.jsonl_writer import JSONLWriter
except ImportError:
    JSONLWriter = None


@pytest.mark.skipif(JSONLWriter is None, reason="JSONLWriter 尚未实现")
class TestJSONLWriterContract:
    """JSONLWriter 契约测试"""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """创建临时目录"""
        return tmp_path / "messages" / "raw"

    @pytest.fixture
    def writer(self, temp_dir: Path) -> "JSONLWriter":
        """创建 JSONLWriter 实例"""
        return JSONLWriter(base_dir=temp_dir)

    def test_init_signature(self, temp_dir: Path):
        """测试初始化方法签名契约"""
        # 应该接受 base_dir 参数(str 或 Path)
        writer1 = JSONLWriter(base_dir=str(temp_dir))
        assert writer1 is not None

        writer2 = JSONLWriter(base_dir=temp_dir)
        assert writer2 is not None

        # base_dir 应该有默认值
        writer3 = JSONLWriter()
        assert writer3 is not None

    def test_append_message_signature(self, writer: "JSONLWriter"):
        """测试 append_message 方法签名契约"""
        # 应该接受 dict 类型的 message 参数
        message = {
            "msg_id": "test_123",
            "from_username": "wxid_sender",
            "content": "Hello",
            "create_time": 1737590400
        }

        # 应该返回 None (静默成功)
        result = writer.append_message(message)
        assert result is None

    def test_append_message_creates_file(self, writer: "JSONLWriter", temp_dir: Path):
        """测试 append_message 创建文件契约"""
        message = {
            "msg_id": "test_123",
            "from_username": "wxid_sender",
            "content": "Hello",
            "create_time": 1737590400
        }

        writer.append_message(message)

        # 应该创建当日 JSONL 文件 (YYYY-MM-DD.jsonl)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        expected_file = temp_dir / f"{today}.jsonl"

        assert expected_file.exists(), "JSONL 文件应该被创建"

    def test_append_message_writes_json_line(self, writer: "JSONLWriter", temp_dir: Path):
        """测试 append_message 写入 JSON 行契约"""
        message = {
            "msg_id": "test_123",
            "from_username": "wxid_sender",
            "content": "Hello",
            "create_time": 1737590400
        }

        writer.append_message(message)

        # 读取文件内容
        today = datetime.utcnow().strftime("%Y-%m-%d")
        jsonl_file = temp_dir / f"{today}.jsonl"

        with open(jsonl_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 应该有一行
        assert len(lines) == 1

        # 应该是有效的 JSON
        parsed = json.loads(lines[0])
        assert parsed["msg_id"] == "test_123"
        assert parsed["from_username"] == "wxid_sender"
        assert parsed["content"] == "Hello"

    def test_append_message_appends_to_existing_file(self, writer: "JSONLWriter", temp_dir: Path):
        """测试 append_message 追加到现有文件契约"""
        message1 = {"msg_id": "msg_1", "content": "First"}
        message2 = {"msg_id": "msg_2", "content": "Second"}

        writer.append_message(message1)
        writer.append_message(message2)

        # 读取文件
        today = datetime.utcnow().strftime("%Y-%m-%d")
        jsonl_file = temp_dir / f"{today}.jsonl"

        with open(jsonl_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 应该有两行
        assert len(lines) == 2

        # 验证内容
        msg1 = json.loads(lines[0])
        msg2 = json.loads(lines[1])
        assert msg1["msg_id"] == "msg_1"
        assert msg2["msg_id"] == "msg_2"

    def test_append_message_error_handling(self, writer: "JSONLWriter"):
        """测试 append_message 错误处理契约"""
        # 传入不可序列化的对象应该抛出 ValueError
        invalid_message = {
            "msg_id": "test_123",
            "invalid_field": object()  # 不可序列化
        }

        with pytest.raises((ValueError, TypeError)):
            writer.append_message(invalid_message)

    def test_append_batch_signature(self, writer: "JSONLWriter"):
        """测试 append_batch 方法签名契约"""
        # 应该接受 list[dict] 类型的 messages 参数
        messages = [
            {"msg_id": "msg_1", "content": "First"},
            {"msg_id": "msg_2", "content": "Second"},
        ]

        # 应该返回 None (静默成功)
        result = writer.append_batch(messages)
        assert result is None

    def test_append_batch_writes_multiple_lines(self, writer: "JSONLWriter", temp_dir: Path):
        """测试 append_batch 写入多行契约"""
        messages = [
            {"msg_id": "msg_1", "content": "First"},
            {"msg_id": "msg_2", "content": "Second"},
            {"msg_id": "msg_3", "content": "Third"},
        ]

        writer.append_batch(messages)

        # 读取文件
        today = datetime.utcnow().strftime("%Y-%m-%d")
        jsonl_file = temp_dir / f"{today}.jsonl"

        with open(jsonl_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 应该有三行
        assert len(lines) == 3

        # 验证内容
        for i, line in enumerate(lines):
            msg = json.loads(line)
            assert msg["msg_id"] == f"msg_{i+1}"

    def test_append_batch_empty_list(self, writer: "JSONLWriter"):
        """测试 append_batch 空列表契约"""
        # 空列表应该静默成功,不抛出异常
        writer.append_batch([])

    def test_thread_safety_concurrent_writes(self, writer: "JSONLWriter", temp_dir: Path):
        """测试并发写入的线程安全契约"""
        import threading

        messages = [{"msg_id": f"msg_{i}", "content": f"Message {i}"} for i in range(100)]

        def write_messages(msgs: list[dict[str, Any]]):
            for msg in msgs:
                writer.append_message(msg)

        # 创建多个线程并发写入
        threads = []
        chunk_size = 20
        for i in range(0, len(messages), chunk_size):
            chunk = messages[i:i+chunk_size]
            thread = threading.Thread(target=write_messages, args=(chunk,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 读取文件
        today = datetime.utcnow().strftime("%Y-%m-%d")
        jsonl_file = temp_dir / f"{today}.jsonl"

        with open(jsonl_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 应该有 100 行(无数据丢失)
        assert len(lines) == 100

        # 所有行应该是有效的 JSON
        msg_ids = set()
        for line in lines:
            msg = json.loads(line)
            msg_ids.add(msg["msg_id"])

        # 所有消息 ID 应该唯一
        assert len(msg_ids) == 100

    def test_file_lock_timeout(self, writer: "JSONLWriter", temp_dir: Path):
        """测试文件锁超时契约"""
        # 这个测试验证在文件被锁定时的行为
        # 具体实现取决于 file_lock 的超时机制
        pass  # 可选测试,取决于实现细节

    def test_atomic_write_on_failure(self, writer: "JSONLWriter", temp_dir: Path):
        """测试写入失败时的原子性契约"""
        # 写入失败不应该产生部分写入的文件
        # 这个测试可能需要 mock 文件系统错误
        pass  # 可选测试,取决于实现细节


@pytest.mark.skipif(JSONLWriter is None, reason="JSONLWriter 尚未实现")
class TestJSONLWriterPerformanceContract:
    """JSONLWriter 性能契约测试"""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """创建临时目录"""
        return tmp_path / "messages" / "raw"

    @pytest.fixture
    def writer(self, temp_dir: Path) -> "JSONLWriter":
        """创建 JSONLWriter 实例"""
        return JSONLWriter(base_dir=temp_dir)

    def test_single_message_write_performance(self, writer: "JSONLWriter", benchmark):
        """测试单条消息写入性能契约 (<10ms)"""
        message = {
            "msg_id": "test_123",
            "from_username": "wxid_sender",
            "content": "Hello World",
            "create_time": 1737590400
        }

        # 使用 pytest-benchmark 测试性能
        result = benchmark(writer.append_message, message)

        # 性能契约: 单条消息写入应该 <10ms
        # 注意: benchmark.stats.mean 单位是秒
        assert benchmark.stats.mean < 0.01, \
            f"单条消息写入超时: {benchmark.stats.mean*1000:.2f}ms > 10ms"

    def test_batch_write_performance(self, writer: "JSONLWriter", benchmark):
        """测试批量写入性能契约"""
        messages = [
            {"msg_id": f"msg_{i}", "content": f"Message {i}"}
            for i in range(1000)
        ]

        # 批量写入 1000 条消息
        result = benchmark(writer.append_batch, messages)

        # 性能契约: 批量写入应该比单条写入快
        # 平均每条消息 <5ms
        avg_per_message = benchmark.stats.mean / len(messages)
        assert avg_per_message < 0.005, \
            f"批量写入平均每条消息超时: {avg_per_message*1000:.2f}ms > 5ms"
