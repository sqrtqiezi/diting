"""
WebhookConfig 单元测试
"""

import pytest
from diting.endpoints.wechat.webhook_config import WebhookConfig
from pydantic import ValidationError


def test_webhook_config_defaults():
    """测试默认配置值"""
    config = WebhookConfig()

    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.webhook_path == "/webhook/wechat"
    assert config.health_check_path == "/health"
    assert config.log_file == "logs/wechat_webhook.log"
    assert config.log_max_size_mb == 100
    assert config.log_backup_count == 10
    assert config.log_level == "INFO"
    assert config.service_name == "diting-webhook"
    assert config.service_version == "1.0.0"


def test_webhook_config_custom_values():
    """测试自定义配置值"""
    config = WebhookConfig(
        host="127.0.0.1",
        port=9000,
        webhook_path="/api/webhook",
        log_level="DEBUG",
    )

    assert config.host == "127.0.0.1"
    assert config.port == 9000
    assert config.webhook_path == "/api/webhook"
    assert config.log_level == "DEBUG"


def test_webhook_config_port_validation():
    """测试端口号验证"""
    # 有效端口
    config = WebhookConfig(port=8080)
    assert config.port == 8080

    # 最小端口
    config = WebhookConfig(port=1)
    assert config.port == 1

    # 最大端口
    config = WebhookConfig(port=65535)
    assert config.port == 65535

    # 无效端口 - 太小
    with pytest.raises(ValidationError):
        WebhookConfig(port=0)

    # 无效端口 - 太大
    with pytest.raises(ValidationError):
        WebhookConfig(port=65536)


def test_webhook_config_log_max_size_validation():
    """测试日志文件大小验证"""
    # 有效大小
    config = WebhookConfig(log_max_size_mb=50)
    assert config.log_max_size_mb == 50

    # 无效大小 - 必须大于 0
    with pytest.raises(ValidationError):
        WebhookConfig(log_max_size_mb=0)

    with pytest.raises(ValidationError):
        WebhookConfig(log_max_size_mb=-1)


def test_webhook_config_backup_count_validation():
    """测试日志备份数量验证"""
    # 有效备份数量
    config = WebhookConfig(log_backup_count=5)
    assert config.log_backup_count == 5

    # 0 个备份也有效(不轮转)
    config = WebhookConfig(log_backup_count=0)
    assert config.log_backup_count == 0

    # 无效备份数量
    with pytest.raises(ValidationError):
        WebhookConfig(log_backup_count=-1)
