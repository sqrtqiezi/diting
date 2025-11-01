"""
Webhook configuration model

Provides Webhook service configuration management with support for
loading from config files and environment variables.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class WebhookConfig(BaseSettings):
    """Webhook configuration model (simplified - no authentication)"""

    # Service configuration
    host: str = Field(default="0.0.0.0", description="Listen address")
    port: int = Field(default=8000, ge=1, le=65535, description="Listen port")
    webhook_path: str = Field(default="/webhook/wechat", description="Webhook path")
    health_check_path: str = Field(default="/health", description="Health check path")

    # Logging configuration
    log_file: str = Field(default="logs/wechat_webhook.log", description="Log file path")
    log_max_size_mb: int = Field(default=100, gt=0, description="Max log file size (MB)")
    log_backup_count: int = Field(default=10, ge=0, description="Log backup count")
    log_level: str = Field(default="INFO", description="Log level")

    # Service information
    service_name: str = Field(default="diting-webhook", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")

    model_config = {
        "env_prefix": "WEBHOOK_",
        "extra": "ignore",  # Ignore extra fields
    }
