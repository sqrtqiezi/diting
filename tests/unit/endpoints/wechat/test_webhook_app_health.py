"""
Webhook 应用健康检查单元测试
"""

from unittest.mock import patch

import pytest
from diting.endpoints.wechat.webhook_app import app
from fastapi.testclient import TestClient


class TestHealthCheckLogic:
    """健康检查逻辑单元测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        with TestClient(app) as c:
            yield c

    @patch("diting.endpoints.wechat.webhook_app.check_log_writable")
    def test_health_check_returns_healthy_when_log_writable(self, mock_check_log_writable, client):
        """测试当日志可写时返回健康状态"""
        # Mock log_writable 返回 True
        mock_check_log_writable.return_value = (True, None)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["log_writable"] is True
        assert "error" not in data or data["error"] is None

    @patch("diting.endpoints.wechat.webhook_app.check_log_writable")
    def test_health_check_returns_unhealthy_when_log_not_writable(
        self, mock_check_log_writable, client
    ):
        """测试当日志不可写时返回不健康状态"""
        # Mock log_writable 返回 False
        mock_check_log_writable.return_value = (False, "Permission denied")

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["log_writable"] is False
        assert data["error"] == "Permission denied"

    def test_health_check_includes_version(self, client):
        """测试健康检查包含版本信息"""
        response = client.get("/health")

        data = response.json()
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_health_check_includes_uptime(self, client):
        """测试健康检查包含运行时间"""
        # 触发 lifespan
        client.post("/webhook/wechat", json={"test": "init"})

        response = client.get("/health")

        data = response.json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], int)
        assert data["uptime_seconds"] >= 0

    def test_health_check_includes_message_count(self, client):
        """测试健康检查包含消息计数"""
        # 发送几个消息
        for i in range(3):
            client.post("/webhook/wechat", json={"id": i})

        response = client.get("/health")

        data = response.json()
        assert "message_count" in data
        assert isinstance(data["message_count"], int)
        assert data["message_count"] >= 3  # 至少有我们发送的 3 个消息
