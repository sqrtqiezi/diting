"""微信 API 配置加载

使用 Pydantic Settings 从 YAML 文件加载和验证配置。
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class TimeoutConfig(BaseModel):
    """超时配置"""

    connect: int = Field(default=10, ge=1, le=60, description="连接超时(秒)")
    read: int = Field(default=30, ge=1, le=300, description="读取超时(秒)")


class RetryConfig(BaseModel):
    """重试配置"""

    max_attempts: int = Field(default=3, ge=1, le=10, description="最大重试次数")
    backoff_factor: float = Field(default=0.5, ge=0, le=5.0, description="退避因子")
    status_codes: list[int] = Field(
        default_factory=lambda: [502, 503, 504], description="需要重试的 HTTP 状态码"
    )


class APIConfig(BaseModel):
    """API 配置"""

    base_url: str = Field(..., description="API 基础 URL")
    app_key: str = Field(..., min_length=10, description="API Key")
    app_secret: str = Field(..., min_length=20, description="API Secret")
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig, description="超时配置")
    retry: RetryConfig = Field(default_factory=RetryConfig, description="重试配置")


class DeviceConfig(BaseModel):
    """设备配置"""

    guid: str = Field(..., description="设备 GUID")
    name: str = Field(default="", description="设备名称")


class LoggingConfig(BaseModel):
    """日志配置"""

    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(default="json", description="日志格式")
    output: str = Field(default="logs/wechat_api.log", description="日志输出路径")


class WeChatConfig(BaseSettings):
    """微信 API 完整配置

    从 YAML 文件加载配置并验证。
    """

    api: APIConfig
    devices: list[DeviceConfig] = Field(default_factory=list, description="设备列表")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="日志配置")

    model_config = {"extra": "ignore"}  # 忽略额外字段

    @classmethod
    def load_from_yaml(cls, config_path: str | Path) -> "WeChatConfig":
        """从 YAML 文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            WeChatConfig: 配置对象

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置格式无效
            ValidationError: 配置验证失败
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        try:
            with open(config_path, encoding="utf-8") as f:
                config_data: dict[str, Any] = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"无效的 YAML 格式: {e}") from e

        return cls(**config_data)
