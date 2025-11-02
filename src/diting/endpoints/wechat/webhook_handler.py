"""
Webhook request handler

Process raw HTTP requests, parse multiple formats, and prepare for logging.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs

from .webhook_logger import get_webhook_logger


@dataclass
class WebhookRequest:
    """Webhook raw request record

    Records complete HTTP request information without format assumptions.
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )
    client_ip: str = ""
    method: str = "POST"
    path: str = "/webhook/wechat"
    headers: dict[str, str] = field(default_factory=dict)
    body_bytes_length: int = 0
    body_text: str = ""
    content_type: str | None = None
    parsed_json: dict[str, Any] | None = None
    parsed_form: dict[str, str] | None = None
    parse_error: str | None = None

    def to_log_dict(self) -> dict[str, Any]:
        """Convert to log dictionary"""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "client_ip": self.client_ip,
            "method": self.method,
            "path": self.path,
            "headers": self.headers,
            "body_length": self.body_bytes_length,
            "body_text": self.body_text,
            "content_type": self.content_type,
            "parsed_json": self.parsed_json,
            "parsed_form": self.parsed_form,
            "parse_error": self.parse_error,
        }


def log_webhook_request(webhook_request: WebhookRequest, body_bytes: bytes):
    """
    记录 webhook 请求到日志

    包含多格式解析(JSON/Form/Text)和容错处理。

    Args:
        webhook_request: WebhookRequest 对象
        body_bytes: 原始请求体字节
    """
    logger = get_webhook_logger()

    # 尝试解码为文本
    try:
        webhook_request.body_text = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # 如果无法解码为 UTF-8,使用替换模式
        webhook_request.body_text = body_bytes.decode("utf-8", errors="replace")

    # 尝试解析为 JSON
    if webhook_request.content_type and "json" in webhook_request.content_type.lower():
        try:
            webhook_request.parsed_json = json.loads(webhook_request.body_text)
        except json.JSONDecodeError as e:
            webhook_request.parse_error = f"JSON decode error: {e}"

    # 尝试解析为 Form(URL-encoded)
    elif webhook_request.content_type and (
        "form" in webhook_request.content_type.lower()
        or "urlencoded" in webhook_request.content_type.lower()
    ):
        try:
            parsed = parse_qs(webhook_request.body_text)
            # 将列表值转换为单个字符串(取第一个值)
            webhook_request.parsed_form = {k: v[0] if v else "" for k, v in parsed.items()}
        except Exception as e:
            webhook_request.parse_error = f"Form parse error: {e}"

    # 如果没有明确的 content-type,尝试猜测 JSON
    elif webhook_request.body_text and webhook_request.body_text.strip().startswith(("{", "[")):
        try:  # noqa: SIM105
            webhook_request.parsed_json = json.loads(webhook_request.body_text)
        except json.JSONDecodeError:
            # 猜测错误,不设置 parse_error(不是错误,只是猜测失败)
            pass

    # 记录到日志
    logger.info(
        "webhook_request_received",
        **webhook_request.to_log_dict(),
    )
