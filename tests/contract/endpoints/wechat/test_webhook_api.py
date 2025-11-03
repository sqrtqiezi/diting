"""
Webhook API 契约测试

验证 API 端点符合 OpenAPI 规范定义。
"""

import pytest
from diting.endpoints.wechat.webhook_app import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端(触发 lifespan 事件)"""
    with TestClient(app) as c:
        yield c


class TestWebhookEndpoint:
    """POST /webhook/wechat 端点契约测试"""

    def test_webhook_accepts_json_post(self, client):
        """测试接受 JSON 格式的 POST 请求"""
        response = client.post(
            "/webhook/wechat",
            json={"msg": "hello", "type": 1, "from": "user1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "request_id" in data

    def test_webhook_accepts_form_post(self, client):
        """测试接受 Form 格式的 POST 请求"""
        response = client.post(
            "/webhook/wechat",
            data={"key1": "value1", "key2": "value2"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "request_id" in data

    def test_webhook_accepts_text_post(self, client):
        """测试接受纯文本格式的 POST 请求"""
        response = client.post(
            "/webhook/wechat",
            content="plain text message",
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "request_id" in data

    def test_webhook_accepts_binary_post(self, client):
        """测试接受二进制格式的 POST 请求"""
        response = client.post(
            "/webhook/wechat",
            content=b"\x00\x01\x02\x03",
            headers={"Content-Type": "application/octet-stream"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "request_id" in data

    def test_webhook_accepts_empty_body(self, client):
        """测试接受空请求体"""
        response = client.post("/webhook/wechat")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "request_id" in data

    def test_webhook_accepts_malformed_json(self, client):
        """测试接受格式错误的 JSON(不应崩溃)"""
        response = client.post(
            "/webhook/wechat",
            content="{invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "request_id" in data

    def test_webhook_response_schema(self, client):
        """测试响应符合 WebhookResponse schema"""
        response = client.post(
            "/webhook/wechat",
            json={"test": "data"},
        )

        assert response.status_code == 200
        data = response.json()

        # 验证必需字段
        assert "status" in data
        assert "request_id" in data

        # 验证字段类型
        assert isinstance(data["status"], str)
        assert isinstance(data["request_id"], str)
        assert data["status"] == "ok"

    def test_webhook_returns_quickly(self, client):
        """测试 webhook 快速响应(< 1 秒)"""
        import time

        start = time.time()
        response = client.post(
            "/webhook/wechat",
            json={"large": "data" * 1000},
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # 应在 1 秒内返回


class TestHealthEndpoint:
    """GET /health 端点契约测试"""

    def test_health_returns_200(self, client):
        """测试健康检查返回 200"""
        response = client.get("/health")

        # 注意:此测试会失败,因为 /health 端点尚未实现
        # 这是预期的,符合 TDD 原则
        assert response.status_code == 200

    def test_health_response_schema(self, client):
        """测试健康检查响应符合 HealthStatus schema"""
        response = client.get("/health")

        if response.status_code == 200:
            data = response.json()

            # 验证必需字段
            assert "status" in data
            assert "version" in data
            assert "uptime_seconds" in data
            assert "message_count" in data
            assert "log_writable" in data

            # 验证字段类型
            assert isinstance(data["status"], str)
            assert isinstance(data["version"], str)
            assert isinstance(data["uptime_seconds"], int)
            assert isinstance(data["message_count"], int)
            assert isinstance(data["log_writable"], bool)
