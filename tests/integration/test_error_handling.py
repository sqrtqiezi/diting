"""错误处理集成测试

测试格式错误消息的处理流程：解析错误、验证错误、schema 错误
"""

import json
from pathlib import Path

import pytest

from src.services.storage.error_handler import (
    ErrorHandler,
    safe_parse_message,
    validate_required_fields,
)


class TestErrorHandlingIntegration:
    """测试错误处理集成流程"""

    @pytest.fixture
    def error_log_path(self, tmp_path: Path) -> Path:
        """创建错误日志路径"""
        return tmp_path / "errors" / "error.log"

    @pytest.fixture
    def storage_dirs(self, tmp_path: Path) -> dict[str, Path]:
        """创建存储目录"""
        return {
            "jsonl": tmp_path / "messages" / "raw",
            "parquet": tmp_path / "messages" / "parquet",
        }

    def test_parse_error_handling(self, error_log_path: Path):
        """测试解析错误处理"""
        error_handler = ErrorHandler(error_log_path)

        # 测试无效 JSON
        invalid_json = '{"msg_id": "msg_001", invalid json}'
        result = safe_parse_message(invalid_json, error_handler, line_number=1)

        assert result is None
        assert error_log_path.exists()

        # 验证错误日志
        error_count = error_handler.get_error_count()
        assert error_count == 1

        error_types = error_handler.get_errors_by_type()
        assert error_types["parse_error"] == 1

    def test_validation_error_handling(self, error_log_path: Path):
        """测试验证错误处理"""
        error_handler = ErrorHandler(error_log_path)

        # 测试缺少必需字段
        incomplete_message = {"msg_id": "msg_001", "content": "test"}
        required_fields = ["msg_id", "from_username", "to_username", "create_time"]

        is_valid = validate_required_fields(incomplete_message, required_fields, error_handler)

        assert is_valid is False
        assert error_log_path.exists()

        # 验证错误日志
        error_types = error_handler.get_errors_by_type()
        assert error_types["schema_error"] == 1

    def test_mixed_valid_and_invalid_messages(
        self, storage_dirs: dict[str, Path], error_log_path: Path
    ):
        """测试混合有效和无效消息的处理"""
        jsonl_dir = storage_dirs["jsonl"]
        error_handler = ErrorHandler(error_log_path)

        # 创建混合消息的 JSONL 文件
        jsonl_file = jsonl_dir / "messages_2026-01-23.jsonl"
        jsonl_file.parent.mkdir(parents=True, exist_ok=True)

        base_timestamp = 1737590400  # 2025-01-23 00:00:00 UTC

        messages = [
            # 有效消息
            {
                "msg_id": "msg_001",
                "from_username": "wxid_sender_1",
                "to_username": "wxid_receiver_1",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": base_timestamp,
                "is_chatroom_msg": 0,
                "content": "Valid message 1",
                "desc": "",
                "source": "0",
                "guid": "guid_1",
                "notify_type": 100,
            },
            # 有效消息
            {
                "msg_id": "msg_002",
                "from_username": "wxid_sender_2",
                "to_username": "wxid_receiver_2",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": base_timestamp + 1,
                "is_chatroom_msg": 0,
                "content": "Valid message 2",
                "desc": "",
                "source": "0",
                "guid": "guid_2",
                "notify_type": 100,
            },
        ]

        # 写入有效消息和无效 JSON
        with open(jsonl_file, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            # 添加无效 JSON
            f.write('{"msg_id": "msg_003", invalid json}\n')
            # 添加另一个有效消息
            valid_msg = messages[0].copy()
            valid_msg["msg_id"] = "msg_004"
            valid_msg["create_time"] = base_timestamp + 2
            f.write(json.dumps(valid_msg, ensure_ascii=False) + "\n")

        # 处理消息（使用 safe_parse_message）
        valid_messages = []
        required_fields = ["msg_id", "from_username", "to_username", "create_time"]

        with open(jsonl_file, encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                message = safe_parse_message(line.strip(), error_handler, line_num)
                if message and validate_required_fields(message, required_fields, error_handler):
                    valid_messages.append(message)

        # 验证结果
        assert len(valid_messages) == 3  # 3 个有效消息
        assert error_handler.get_error_count() == 1  # 1 个解析错误

        error_types = error_handler.get_errors_by_type()
        assert error_types.get("parse_error", 0) == 1

    def test_schema_error_with_missing_fields(self, error_log_path: Path):
        """测试缺少多个字段的 schema 错误"""
        error_handler = ErrorHandler(error_log_path)

        # 消息缺少多个必需字段
        incomplete_message = {
            "msg_id": "msg_001",
            "content": "test message",
        }

        required_fields = [
            "msg_id",
            "from_username",
            "to_username",
            "msg_type",
            "create_time",
            "content",
        ]

        is_valid = validate_required_fields(incomplete_message, required_fields, error_handler)

        assert is_valid is False

        # 读取错误日志验证详细信息
        with open(error_log_path, encoding="utf-8") as f:
            error_entry = json.loads(f.readline())

        assert error_entry["error_type"] == "schema_error"
        assert "from_username" in error_entry["missing_fields"]
        assert "to_username" in error_entry["missing_fields"]
        assert "msg_type" in error_entry["missing_fields"]
        assert "create_time" in error_entry["missing_fields"]

    def test_error_recovery_and_continuation(
        self, storage_dirs: dict[str, Path], error_log_path: Path
    ):
        """测试错误恢复和继续处理"""
        jsonl_dir = storage_dirs["jsonl"]
        error_handler = ErrorHandler(error_log_path)

        # 创建包含错误的 JSONL 文件
        jsonl_file = jsonl_dir / "messages_2026-01-23.jsonl"
        jsonl_file.parent.mkdir(parents=True, exist_ok=True)

        base_timestamp = 1737590400

        # 写入 10 个有效消息和 3 个无效消息
        with open(jsonl_file, "w", encoding="utf-8") as f:
            for i in range(15):
                if i in [3, 7, 11]:  # 第 4、8、12 条是无效的
                    f.write('{"msg_id": "invalid", broken json}\n')
                else:
                    msg = {
                        "msg_id": f"msg_{i:03d}",
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
                    f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        # 处理消息并跳过错误
        valid_messages = []
        required_fields = ["msg_id", "from_username", "to_username", "create_time"]

        with open(jsonl_file, encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                message = safe_parse_message(line.strip(), error_handler, line_num)
                if message and validate_required_fields(message, required_fields, error_handler):
                    valid_messages.append(message)

        # 验证处理结果
        assert len(valid_messages) == 12  # 12 个有效消息
        assert error_handler.get_error_count() == 3  # 3 个解析错误

        # 验证有效消息的 ID
        valid_ids = {msg["msg_id"] for msg in valid_messages}
        assert "msg_000" in valid_ids
        assert "msg_001" in valid_ids
        assert "msg_002" in valid_ids
        # msg_003 位置是无效的
        assert "msg_004" in valid_ids

    def test_error_log_format(self, error_log_path: Path):
        """测试错误日志格式"""
        error_handler = ErrorHandler(error_log_path)

        # 触发不同类型的错误
        # 1. 解析错误
        safe_parse_message('{"invalid": json}', error_handler, line_number=1)

        # 2. Schema 错误
        incomplete_msg = {"msg_id": "msg_001"}
        validate_required_fields(incomplete_msg, ["msg_id", "content"], error_handler)

        # 3. 验证错误
        error_handler.handle_validation_error(
            {"msg_id": "msg_002", "invalid_field": "value"},
            ValueError("Invalid field"),
            msg_id="msg_002",
        )

        # 验证错误日志格式
        assert error_handler.get_error_count() == 3

        with open(error_log_path, encoding="utf-8") as f:
            lines = f.readlines()

        # 验证每行都是有效的 JSON
        for line in lines:
            error_entry = json.loads(line)
            assert "error_type" in error_entry
            assert "error_message" in error_entry
            assert "timestamp" in error_entry

        # 验证错误类型统计
        error_types = error_handler.get_errors_by_type()
        assert error_types["parse_error"] == 1
        assert error_types["schema_error"] == 1
        assert error_types["validation_error"] == 1

    def test_large_batch_with_errors(self, storage_dirs: dict[str, Path], error_log_path: Path):
        """测试大批量数据中的错误处理"""
        jsonl_dir = storage_dirs["jsonl"]
        error_handler = ErrorHandler(error_log_path)

        # 创建包含 1000 条消息的文件，其中 10% 是无效的
        jsonl_file = jsonl_dir / "messages_2026-01-23.jsonl"
        jsonl_file.parent.mkdir(parents=True, exist_ok=True)

        base_timestamp = 1737590400
        total_messages = 1000
        error_rate = 0.1  # 10% 错误率

        with open(jsonl_file, "w", encoding="utf-8") as f:
            for i in range(total_messages):
                if i % 10 == 0:  # 每 10 条有 1 条错误
                    f.write('{"msg_id": "invalid", broken}\n')
                else:
                    msg = {
                        "msg_id": f"msg_{i:04d}",
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
                    f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        # 处理消息
        valid_count = 0
        required_fields = ["msg_id", "from_username", "to_username", "create_time"]

        with open(jsonl_file, encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                message = safe_parse_message(line.strip(), error_handler, line_num)
                if message and validate_required_fields(message, required_fields, error_handler):
                    valid_count += 1

        # 验证结果
        expected_valid = int(total_messages * (1 - error_rate))
        assert valid_count == expected_valid
        assert error_handler.get_error_count() == int(total_messages * error_rate)

        # 验证错误类型
        error_types = error_handler.get_errors_by_type()
        assert error_types["parse_error"] == int(total_messages * error_rate)
