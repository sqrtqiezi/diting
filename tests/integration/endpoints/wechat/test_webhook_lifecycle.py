"""
Webhook 服务生命周期集成测试
"""

import time

import pytest
from fastapi.testclient import TestClient

from diting.endpoints.wechat.webhook_app import app, app_state


class TestWebhookLifecycle:
    """Webhook 服务生命周期测试"""

    @pytest.fixture(scope="class")
    def client(self):
        """创建测试客户端(类级别共享,确保 lifespan 只运行一次)"""
        with TestClient(app) as c:
            yield c

    def test_app_lifespan_initializes_state(self, client):
        """测试应用启动时初始化状态"""
        # TestClient 会触发 lifespan,在 context manager 内
        # 发送一个请求确保 lifespan 已运行
        response = client.post("/webhook/wechat", json={"init": "test"})
        assert response.status_code == 200

        # 验证 app_state 被初始化
        assert app_state["config"] is not None
        assert app_state["start_time"] > 0
        assert "message_count" in app_state

    def test_app_lifespan_configures_logging(self, client):
        """测试应用启动时配置日志"""
        # 发送一个请求,触发日志记录
        response = client.post("/webhook/wechat", json={"test": "lifecycle"})
        assert response.status_code == 200

        # 验证日志配置被初始化(通过检查配置对象)
        config = app_state["config"]
        assert config.log_file == "logs/wechat_webhook.log"
        assert config.log_max_size_mb == 100
        assert config.log_backup_count == 10

    def test_message_counter_increments(self, client):
        """测试消息计数器递增"""
        initial_count = app_state["message_count"]

        # 发送多个请求
        for i in range(5):
            client.post("/webhook/wechat", json={"id": i})

        # 验证计数器增加
        assert app_state["message_count"] == initial_count + 5

    def test_uptime_tracking(self, client):
        """测试运行时间跟踪"""
        # 发送请求确保 lifespan 已运行
        response = client.post("/webhook/wechat", json={"uptime": "test"})
        assert response.status_code == 200

        start_time = app_state["start_time"]
        assert start_time > 0

        # 等待一小段时间
        time.sleep(0.1)

        # 计算运行时间
        uptime = time.time() - start_time
        assert uptime >= 0.1

    @pytest.mark.skip(reason="Signal handler testing requires actual process")
    def test_graceful_shutdown_on_sigint(self):
        """测试 SIGINT 信号优雅关闭"""
        # 此测试需要实际进程,暂时跳过
        # 将在实际部署测试中验证
        pass

    @pytest.mark.skip(reason="Signal handler testing requires actual process")
    def test_graceful_shutdown_on_sigterm(self):
        """测试 SIGTERM 信号优雅关闭"""
        # 此测试需要实际进程,暂时跳过
        # 将在实际部署测试中验证
        pass
