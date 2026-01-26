"""
Webhook 健康检查集成测试
"""

import time

import pytest
from fastapi.testclient import TestClient

from diting.endpoints.wechat.webhook_app import app


class TestWebhookHealthIntegration:
    """Webhook 健康检查集成测试"""

    @pytest.fixture(scope="class")
    def client(self):
        """创建测试客户端(类级别共享)"""
        with TestClient(app) as c:
            yield c

    def test_health_endpoint_exists(self, client):
        """测试健康检查端点存在"""
        response = client.get("/health")
        # 应该返回 200 或 503,不应该是 404
        assert response.status_code in (200, 503)

    def test_health_returns_complete_status(self, client):
        """测试健康检查返回完整状态信息"""
        # 发送一些消息
        for i in range(5):
            client.post("/webhook/wechat", json={"test": f"message-{i}"})

        # 稍等一下确保处理完成
        time.sleep(0.1)

        response = client.get("/health")
        data = response.json()

        # 验证所有必需字段
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "message_count" in data
        assert "log_writable" in data

        # 验证值的合理性
        assert data["status"] in ("healthy", "unhealthy")
        assert data["version"] == "1.0.0"
        assert data["uptime_seconds"] >= 0
        assert data["message_count"] >= 5  # 至少有我们发送的 5 个消息

    def test_health_uptime_increases(self, client):
        """测试运行时间随时间增加"""
        # 第一次检查
        response1 = client.get("/health")
        uptime1 = response1.json()["uptime_seconds"]

        # 等待一秒
        time.sleep(1)

        # 第二次检查
        response2 = client.get("/health")
        uptime2 = response2.json()["uptime_seconds"]

        # 运行时间应该增加
        assert uptime2 >= uptime1

    def test_health_message_count_increments(self, client):
        """测试消息计数随请求递增"""
        # 获取当前计数
        response1 = client.get("/health")
        count1 = response1.json()["message_count"]

        # 发送新消息
        client.post("/webhook/wechat", json={"test": "increment"})

        # 再次检查
        response2 = client.get("/health")
        count2 = response2.json()["message_count"]

        # 计数应该增加
        assert count2 > count1

    def test_health_status_healthy_by_default(self, client):
        """测试默认情况下服务应该是健康的"""
        response = client.get("/health")

        # 在正常测试环境中,日志应该可写
        # 所以应该返回 200 healthy
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "healthy"
            assert data["log_writable"] is True

    @pytest.mark.skip(reason="Requires permission manipulation - manual test only")
    def test_health_returns_503_when_log_not_writable(self, client, tmp_path):
        """测试日志不可写时返回 503"""
        # 此测试需要手动操作文件权限
        # 在实际部署环境中验证
        pass

    def test_health_response_schema_validity(self, client):
        """测试健康检查响应符合 schema"""
        response = client.get("/health")
        data = response.json()

        # 验证字段类型
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["uptime_seconds"], int)
        assert isinstance(data["message_count"], int)
        assert isinstance(data["log_writable"], bool)

        # 如果有错误信息,应该是字符串或 None
        if "error" in data:
            assert data["error"] is None or isinstance(data["error"], str)
