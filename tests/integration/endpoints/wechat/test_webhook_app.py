"""
Webhook 应用集成测试

端到端测试 webhook 消息接收流程。
"""

import time

import pytest
from diting.endpoints.wechat.webhook_app import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端(触发 lifespan 事件)"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def temp_log_file(tmp_path):
    """创建临时日志文件"""
    log_file = tmp_path / "test_webhook.log"
    return str(log_file)


class TestWebhookIntegration:
    """Webhook 集成测试"""

    def test_webhook_end_to_end_json(self, client):
        """测试 JSON 消息的端到端流程"""
        # 发送 JSON 消息
        payload = {"msg": "test message", "type": 1, "from": "user1"}
        response = client.post("/webhook/wechat", json=payload)

        # 验证立即返回 200
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "request_id" in data

        # 注意:日志记录是后台异步的,这里只验证响应
        # 日志验证将在后续任务中完成

    def test_webhook_end_to_end_form(self, client):
        """测试 Form 消息的端到端流程"""
        # 发送 Form 数据
        payload = {"key1": "value1", "key2": "value2"}
        response = client.post("/webhook/wechat", data=payload)

        # 验证立即返回 200
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "request_id" in data

    def test_webhook_end_to_end_text(self, client):
        """测试纯文本消息的端到端流程"""
        # 发送纯文本
        response = client.post(
            "/webhook/wechat",
            content="plain text message",
            headers={"Content-Type": "text/plain"},
        )

        # 验证立即返回 200
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "request_id" in data

    def test_webhook_handles_invalid_json_gracefully(self, client):
        """测试优雅处理无效 JSON"""
        # 发送格式错误的 JSON
        response = client.post(
            "/webhook/wechat",
            content="{invalid json}",
            headers={"Content-Type": "application/json"},
        )

        # 应该不崩溃,仍然返回 200
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_webhook_handles_empty_body(self, client):
        """测试处理空请求体"""
        response = client.post("/webhook/wechat")

        # 空请求体也应该成功处理
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_webhook_handles_large_payload(self, client):
        """测试处理大请求体"""
        # 发送 1MB 的数据
        large_payload = {"data": "x" * (1024 * 1024)}
        response = client.post("/webhook/wechat", json=large_payload)

        # 应该成功处理
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_webhook_concurrent_requests(self, client):
        """测试并发请求处理"""
        import concurrent.futures

        def send_request(i):
            return client.post("/webhook/wechat", json={"id": i})

        # 发送 10 个并发请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_request, i) for i in range(10)]
            results = [f.result() for f in futures]

        # 所有请求都应该成功
        assert all(r.status_code == 200 for r in results)
        assert all(r.json()["status"] == "ok" for r in results)

    def test_webhook_response_time(self, client):
        """测试响应时间 < 100ms"""
        start = time.time()
        response = client.post("/webhook/wechat", json={"test": "data"})
        elapsed = time.time() - start

        assert response.status_code == 200
        # 响应应该在 100ms 内(由于是后台处理)
        assert elapsed < 0.1

    @pytest.mark.skip(reason="Requires log file verification - not yet implemented")
    def test_webhook_logs_to_file(self, client, temp_log_file):
        """测试消息记录到日志文件"""
        # 此测试将在日志功能实现后取消跳过
        pass
