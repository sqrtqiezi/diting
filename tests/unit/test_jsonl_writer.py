"""JSONLWriter 单元测试

测试 JSONL 写入器的核心功能，使用 mock 隔离文件系统依赖。
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.storage.jsonl_writer import JSONLWriter


class TestJSONLWriterInit:
    """测试 JSONLWriter 初始化"""

    def test_init_with_default_base_dir(self):
        """测试使用默认基础目录初始化"""
        with patch("src.services.storage.jsonl_writer.Path.mkdir"):
            writer = JSONLWriter()
            assert writer.base_dir == Path("data/messages/raw")

    def test_init_with_custom_base_dir_string(self, tmp_path: Path):
        """测试使用自定义基础目录（字符串）初始化"""
        custom_dir = str(tmp_path / "custom")
        writer = JSONLWriter(base_dir=custom_dir)
        assert writer.base_dir == Path(custom_dir)

    def test_init_with_custom_base_dir_path(self, tmp_path: Path):
        """测试使用自定义基础目录（Path）初始化"""
        custom_dir = tmp_path / "custom"
        writer = JSONLWriter(base_dir=custom_dir)
        assert writer.base_dir == custom_dir

    def test_init_creates_base_dir(self, tmp_path: Path):
        """测试初始化时创建基础目录"""
        base_dir = tmp_path / "messages" / "raw"
        assert not base_dir.exists()

        JSONLWriter(base_dir=base_dir)

        assert base_dir.exists()
        assert base_dir.is_dir()


class TestJSONLWriterGetCurrentFilePath:
    """测试获取当前文件路径"""

    def test_get_current_file_path_format(self, tmp_path: Path):
        """测试文件路径格式为 YYYY-MM-DD.jsonl"""
        writer = JSONLWriter(base_dir=tmp_path)

        with patch("src.services.storage.jsonl_writer.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2025-01-23"

            file_path = writer._get_current_file_path()

            assert file_path == tmp_path / "2025-01-23.jsonl"
            mock_datetime.now.return_value.strftime.assert_called_once_with("%Y-%m-%d")

    def test_get_current_file_path_uses_utc(self, tmp_path: Path):
        """测试使用 UTC 时区"""
        from datetime import UTC

        writer = JSONLWriter(base_dir=tmp_path)

        with patch("src.services.storage.jsonl_writer.datetime") as mock_datetime:
            writer._get_current_file_path()

            mock_datetime.now.assert_called_once_with(UTC)


class TestJSONLWriterAppendMessage:
    """测试追加单条消息"""

    @pytest.fixture
    def writer(self, tmp_path: Path) -> JSONLWriter:
        """创建 JSONLWriter 实例"""
        return JSONLWriter(base_dir=tmp_path)

    @pytest.fixture
    def sample_message(self) -> dict:
        """创建示例消息"""
        return {
            "msg_id": "test_123",
            "from_username": "wxid_sender",
            "content": "Hello World",
            "create_time": 1737590400,
        }

    def test_append_message_success(self, writer: JSONLWriter, sample_message: dict):
        """测试成功追加消息"""
        # 不应该抛出异常
        writer.append_message(sample_message)

        # 验证文件被创建
        jsonl_file = writer._get_current_file_path()
        assert jsonl_file.exists()

        # 验证内容
        with open(jsonl_file, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["msg_id"] == "test_123"
        assert parsed["content"] == "Hello World"

    def test_append_message_returns_none(self, writer: JSONLWriter, sample_message: dict):
        """测试 append_message 返回 None"""
        result = writer.append_message(sample_message)
        assert result is None

    def test_append_message_multiple_times(self, writer: JSONLWriter):
        """测试多次追加消息"""
        messages = [
            {"msg_id": "msg_1", "content": "First"},
            {"msg_id": "msg_2", "content": "Second"},
            {"msg_id": "msg_3", "content": "Third"},
        ]

        for msg in messages:
            writer.append_message(msg)

        # 验证所有消息都被写入
        jsonl_file = writer._get_current_file_path()
        with open(jsonl_file, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 3

        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed["msg_id"] == f"msg_{i+1}"

    def test_append_message_with_unicode(self, writer: JSONLWriter):
        """测试追加包含 Unicode 字符的消息"""
        message = {
            "msg_id": "test_unicode",
            "content": "你好世界 🌍",
            "emoji": "😀",
        }

        writer.append_message(message)

        jsonl_file = writer._get_current_file_path()
        with open(jsonl_file, encoding="utf-8") as f:
            line = f.readline()

        parsed = json.loads(line)
        assert parsed["content"] == "你好世界 🌍"
        assert parsed["emoji"] == "😀"

    def test_append_message_invalid_json_raises_error(self, writer: JSONLWriter):
        """测试不可序列化的消息抛出 ValueError"""
        invalid_message = {
            "msg_id": "test_123",
            "invalid_field": object(),  # 不可序列化
        }

        with pytest.raises(ValueError, match="无法序列化消息为 JSON"):
            writer.append_message(invalid_message)

    def test_append_message_uses_file_lock(self, writer: JSONLWriter, sample_message: dict):
        """测试使用文件锁"""
        with patch("src.services.storage.jsonl_writer.file_lock") as mock_lock:
            mock_lock.return_value.__enter__ = MagicMock()
            mock_lock.return_value.__exit__ = MagicMock()

            writer.append_message(sample_message)

            # 验证 file_lock 被调用
            assert mock_lock.called
            lock_file = writer._get_current_file_path().with_suffix(".lock")
            mock_lock.assert_called_once_with(lock_file, timeout=10)

    def test_append_message_fsync_called(self, writer: JSONLWriter, sample_message: dict):
        """测试调用 fsync 确保数据写入磁盘"""
        with patch("os.fsync") as mock_fsync:
            writer.append_message(sample_message)

            # 验证 fsync 被调用
            assert mock_fsync.called


class TestJSONLWriterAppendBatch:
    """测试批量追加消息"""

    @pytest.fixture
    def writer(self, tmp_path: Path) -> JSONLWriter:
        """创建 JSONLWriter 实例"""
        return JSONLWriter(base_dir=tmp_path)

    def test_append_batch_success(self, writer: JSONLWriter):
        """测试成功批量追加消息"""
        messages = [
            {"msg_id": "msg_1", "content": "First"},
            {"msg_id": "msg_2", "content": "Second"},
            {"msg_id": "msg_3", "content": "Third"},
        ]

        writer.append_batch(messages)

        # 验证文件内容
        jsonl_file = writer._get_current_file_path()
        with open(jsonl_file, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 3

        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed["msg_id"] == f"msg_{i+1}"

    def test_append_batch_returns_none(self, writer: JSONLWriter):
        """测试 append_batch 返回 None"""
        messages = [{"msg_id": "msg_1"}]
        result = writer.append_batch(messages)
        assert result is None

    def test_append_batch_empty_list(self, writer: JSONLWriter):
        """测试空列表静默成功"""
        writer.append_batch([])

        # 不应该创建文件
        jsonl_file = writer._get_current_file_path()
        # 注意：由于 base_dir 在 __init__ 时创建，文件可能不存在
        if jsonl_file.exists():
            with open(jsonl_file, encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 0

    def test_append_batch_large_batch(self, writer: JSONLWriter):
        """测试大批量写入"""
        messages = [{"msg_id": f"msg_{i}", "content": f"Message {i}"} for i in range(1000)]

        writer.append_batch(messages)

        jsonl_file = writer._get_current_file_path()
        with open(jsonl_file, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 1000

    def test_append_batch_invalid_message_raises_error(self, writer: JSONLWriter):
        """测试批量写入中包含无效消息抛出错误"""
        messages = [
            {"msg_id": "msg_1", "content": "Valid"},
            {"msg_id": "msg_2", "invalid": object()},  # 无效
        ]

        with pytest.raises(ValueError, match="无法序列化消息"):
            writer.append_batch(messages)

    def test_append_batch_uses_file_lock(self, writer: JSONLWriter):
        """测试批量写入使用文件锁"""
        messages = [{"msg_id": "msg_1"}]

        with patch("src.services.storage.jsonl_writer.file_lock") as mock_lock:
            mock_lock.return_value.__enter__ = MagicMock()
            mock_lock.return_value.__exit__ = MagicMock()

            writer.append_batch(messages)

            assert mock_lock.called


class TestJSONLWriterThreadSafety:
    """测试线程安全"""

    @pytest.fixture
    def writer(self, tmp_path: Path) -> JSONLWriter:
        """创建 JSONLWriter 实例"""
        return JSONLWriter(base_dir=tmp_path)

    def test_concurrent_writes(self, writer: JSONLWriter):
        """测试并发写入不丢失数据"""
        import threading

        messages = [{"msg_id": f"msg_{i}", "content": f"Message {i}"} for i in range(100)]

        def write_messages(msgs: list[dict]):
            for msg in msgs:
                writer.append_message(msg)

        # 创建多个线程并发写入
        threads = []
        chunk_size = 20
        for i in range(0, len(messages), chunk_size):
            chunk = messages[i : i + chunk_size]
            thread = threading.Thread(target=write_messages, args=(chunk,))
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


class TestJSONLWriterErrorHandling:
    """测试错误处理"""

    @pytest.fixture
    def writer(self, tmp_path: Path) -> JSONLWriter:
        """创建 JSONLWriter 实例"""
        return JSONLWriter(base_dir=tmp_path)

    def test_append_message_file_write_error(self, writer: JSONLWriter):
        """测试文件写入失败抛出 OSError"""
        message = {"msg_id": "test_123"}

        with (
            patch("builtins.open", side_effect=OSError("Disk full")),
            pytest.raises(OSError),
        ):
            writer.append_message(message)

    def test_append_batch_file_write_error(self, writer: JSONLWriter):
        """测试批量写入失败抛出 OSError"""
        messages = [{"msg_id": "msg_1"}]

        with (
            patch("builtins.open", side_effect=OSError("Disk full")),
            pytest.raises(OSError),
        ):
            writer.append_batch(messages)
