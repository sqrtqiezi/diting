"""
Webhook 存储集成测试

验证 webhook 接收消息后正确持久化到 JSONL 文件。
"""

import json
import time
from datetime import UTC, datetime

import pytest
from diting.endpoints.wechat.webhook_app import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def temp_data_dir(tmp_path):
    """创建临时数据目录"""
    data_dir = tmp_path / "data" / "messages" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture(autouse=True)
def reset_jsonl_writer():
    """在每个测试前后重置 JSONL writer 单例"""
    from diting.endpoints.wechat import webhook_handler

    # 测试前:重置
    webhook_handler._jsonl_writer = None

    yield

    # 测试后:清理
    webhook_handler._jsonl_writer = None


class TestWebhookStorageIntegration:
    """Webhook 存储集成测试"""

    @pytest.mark.skip(
        reason=(
            "TODO: Fix background task testing - TestClient doesn't properly "
            "execute background tasks with global state"
        )
    )
    def test_webhook_persists_json_message_to_jsonl(self, client, temp_data_dir, monkeypatch):
        """测试 webhook 接收 JSON 消息后持久化到 JSONL 文件"""
        # 修改数据目录为临时目录
        from diting.endpoints.wechat import webhook_handler
        from diting.services.storage.jsonl_writer import JSONLWriter

        # 创建测试用的 writer
        test_writer = JSONLWriter(base_dir=temp_data_dir)

        # 直接设置全局变量,而不是 monkeypatch 函数
        webhook_handler._jsonl_writer = test_writer

        # 发送测试消息
        test_message = {
            "msg_id": "test_msg_001",
            "from_username": "wxid_test123",
            "to_username": "filehelper",
            "content": "Test message",
            "create_time": 1737590400,
            "msg_type": 1,
            "is_chatroom_msg": 0,
            "chatroom": "",
            "chatroom_sender": "",
            "desc": "",
            "source": "0",
            "guid": "test-guid-001",
            "notify_type": 100,
        }

        response = client.post("/webhook/wechat", json=test_message)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        # 等待后台任务完成 (FastAPI TestClient 的后台任务是异步的)
        # 给后台任务一些时间来完成文件写入
        time.sleep(0.1)

        # 验证 JSONL 文件已创建
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        jsonl_file = temp_data_dir / f"{today}.jsonl"
        assert jsonl_file.exists(), f"JSONL file not created: {jsonl_file}"

        # 验证消息已写入
        with open(jsonl_file, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1, "Expected 1 message in JSONL file"

            persisted_message = json.loads(lines[0])
            assert persisted_message["msg_id"] == "test_msg_001"
            assert persisted_message["from_username"] == "wxid_test123"
            assert persisted_message["content"] == "Test message"

        # 清理:重置全局变量
        webhook_handler._jsonl_writer = None

    @pytest.mark.skip(
        reason=(
            "TODO: Fix background task testing - JSONLWriter creates directory "
            "on init, can't test failure gracefully"
        )
    )
    def test_webhook_handles_storage_failure_gracefully(self, client, monkeypatch):
        """测试存储失败时 webhook 仍然返回成功响应"""
        from diting.endpoints.wechat import webhook_handler
        from diting.services.storage.jsonl_writer import JSONLWriter

        # 创建一个会失败的 writer (使用无效路径)
        failing_writer = JSONLWriter(base_dir="/invalid/path/that/does/not/exist")

        # 直接设置全局变量
        webhook_handler._jsonl_writer = failing_writer

        # 发送测试消息
        test_message = {"msg_id": "test_msg_002", "content": "Test"}

        response = client.post("/webhook/wechat", json=test_message)

        # 验证 webhook 仍然返回成功（存储失败不应影响响应）
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        # 清理:重置全局变量
        webhook_handler._jsonl_writer = None

    def test_webhook_only_persists_json_messages(self, client, temp_data_dir, monkeypatch):
        """测试 webhook 只持久化 JSON 消息，忽略其他格式"""
        from diting.endpoints.wechat import webhook_handler
        from diting.services.storage.jsonl_writer import JSONLWriter

        # 创建测试用的 writer
        test_writer = JSONLWriter(base_dir=temp_data_dir)

        # 直接设置全局变量
        webhook_handler._jsonl_writer = test_writer

        # 发送纯文本消息（非 JSON）
        response = client.post(
            "/webhook/wechat", content="plain text message", headers={"content-type": "text/plain"}
        )

        assert response.status_code == 200

        # 等待后台任务完成
        time.sleep(0.1)

        # 验证没有创建 JSONL 文件（因为不是 JSON 消息）
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        jsonl_file = temp_data_dir / f"{today}.jsonl"
        assert not jsonl_file.exists(), "JSONL file should not be created for non-JSON messages"

        # 清理:重置全局变量
        webhook_handler._jsonl_writer = None

    @pytest.mark.skip(
        reason=(
            "TODO: Fix background task testing - TestClient doesn't properly "
            "execute background tasks with global state"
        )
    )
    def test_webhook_appends_multiple_messages(self, client, temp_data_dir, monkeypatch):
        """测试 webhook 可以追加多条消息到同一个 JSONL 文件"""
        from diting.endpoints.wechat import webhook_handler
        from diting.services.storage.jsonl_writer import JSONLWriter

        # 创建测试用的 writer
        test_writer = JSONLWriter(base_dir=temp_data_dir)

        # 直接设置全局变量
        webhook_handler._jsonl_writer = test_writer

        # 发送多条消息
        messages = [
            {"msg_id": f"msg_{i}", "content": f"Message {i}", "create_time": 1737590400 + i}
            for i in range(5)
        ]

        for msg in messages:
            response = client.post("/webhook/wechat", json=msg)
            assert response.status_code == 200

        # 等待后台任务完成 (FastAPI TestClient 的后台任务是异步的)
        # 给后台任务一些时间来完成所有文件写入
        time.sleep(0.2)

        # 验证所有消息都已写入
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        jsonl_file = temp_data_dir / f"{today}.jsonl"
        assert jsonl_file.exists()

        with open(jsonl_file, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 5, "Expected 5 messages in JSONL file"

            for i, line in enumerate(lines):
                persisted_message = json.loads(line)
                assert persisted_message["msg_id"] == f"msg_{i}"
                assert persisted_message["content"] == f"Message {i}"

        # 清理:重置全局变量
        webhook_handler._jsonl_writer = None
