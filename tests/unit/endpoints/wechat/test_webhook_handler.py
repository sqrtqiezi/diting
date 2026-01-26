"""
webhook_handler 单元测试
"""

from unittest.mock import patch

import pytest

from diting.endpoints.wechat.webhook_handler import WebhookRequest


class TestWebhookRequest:
    """WebhookRequest dataclass 测试"""

    def test_webhook_request_creation(self):
        """测试创建 WebhookRequest"""
        req = WebhookRequest(
            client_ip="192.168.1.1",
            headers={"content-type": "application/json"},
            body_text='{"msg":"hello"}',
            body_bytes_length=15,
        )

        assert req.client_ip == "192.168.1.1"
        assert req.headers == {"content-type": "application/json"}
        assert req.body_text == '{"msg":"hello"}'
        assert req.body_bytes_length == 15
        assert req.method == "POST"  # 默认值
        assert req.path == "/webhook/wechat"  # 默认值

    def test_webhook_request_generates_id_and_timestamp(self):
        """测试自动生成 request_id 和 timestamp"""
        req = WebhookRequest()

        assert req.request_id is not None
        assert len(req.request_id) == 36  # UUID 格式
        assert req.timestamp is not None
        assert req.timestamp.endswith("Z")  # UTC 格式

    def test_webhook_request_to_log_dict(self):
        """测试转换为日志字典"""
        req = WebhookRequest(
            client_ip="192.168.1.1",
            headers={"content-type": "application/json"},
            body_text='{"msg":"hello"}',
            body_bytes_length=15,
            content_type="application/json",
            parsed_json={"msg": "hello"},
        )

        log_dict = req.to_log_dict()

        assert log_dict["client_ip"] == "192.168.1.1"
        assert log_dict["headers"] == {"content-type": "application/json"}
        assert log_dict["body_text"] == '{"msg":"hello"}'
        assert log_dict["body_length"] == 15
        assert log_dict["content_type"] == "application/json"
        assert log_dict["parsed_json"] == {"msg": "hello"}
        assert "request_id" in log_dict
        assert "timestamp" in log_dict


class TestLogWebhookRequest:
    """log_webhook_request 函数测试(将在实现时添加)"""

    @pytest.mark.skip(reason="Function not yet implemented")
    def test_log_webhook_request_with_json(self):
        """测试记录 JSON 格式请求"""
        # 此测试将在 T018 实现后取消跳过
        pass

    @pytest.mark.skip(reason="Function not yet implemented")
    def test_log_webhook_request_with_form(self):
        """测试记录 Form 格式请求"""
        # 此测试将在 T018 实现后取消跳过
        pass

    @pytest.mark.skip(reason="Function not yet implemented")
    def test_log_webhook_request_with_invalid_json(self):
        """测试记录无效 JSON 请求"""
        # 此测试将在 T018 实现后取消跳过
        pass

    @pytest.mark.skip(reason="Function not yet implemented")
    @patch("diting.endpoints.wechat.webhook_handler.get_webhook_logger")
    def test_log_webhook_request_calls_logger(self, mock_get_logger):
        """测试 log_webhook_request 调用 logger"""
        # 此测试将在 T018 实现后取消跳过
        pass
