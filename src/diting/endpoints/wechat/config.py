"""微信 API 配置加载

使用 Pydantic Settings 从 YAML 文件加载和验证配置。
"""

from pathlib import Path
from typing import Any, Literal

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
    cloud_base_url: str = Field(
        default="http://101.132.162.209:35789/",
        description="Cloud API 基础 URL (用于 /cloud 开头的接口)",
    )
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


class AliyunConfig(BaseModel):
    """阿里云通用凭证配置（OSS / OCR 等共用）"""

    access_key_id: str = Field(..., description="AccessKey ID")
    access_key_secret: str = Field(..., description="AccessKey Secret")


class OSSConfig(BaseModel):
    """阿里云 OSS 配置（用于发送文件前的外链存储）"""

    endpoint: str = Field(
        ...,
        description="OSS Endpoint (例如 oss-cn-hangzhou.aliyuncs.com)",
    )
    bucket: str = Field(..., description="OSS Bucket 名称")
    # 允许从环境变量回退读取（与 process-ocr 复用同一套 AK/SK），避免配置重复。
    # 兼容旧配置：建议迁移到 wechat.yaml 的 aliyun.access_key_id/access_key_secret。
    access_key_id: str | None = Field(
        default=None,
        description="AccessKey ID（可选，未填则读环境变量）",
    )
    access_key_secret: str | None = Field(
        default=None, description="AccessKey Secret（可选，未填则读环境变量）"
    )
    prefix: str = Field(default="diting/wechat-send", description="对象 Key 前缀")
    url_mode: Literal["public", "signed"] = Field(
        default="public",
        description="外链模式: public=public-read 直链; signed=预签名 URL（对象保持私有）",
    )
    signed_url_expires: int = Field(
        default=300,
        ge=30,
        le=24 * 3600,
        description="signed URL 有效期（秒），默认 300 秒",
    )
    public_base_url: str | None = Field(
        default=None,
        description="可选：外链 URL 基础地址（默认使用 https://{bucket}.{endpoint}）",
    )


class WeChatConfig(BaseSettings):
    """微信 API 完整配置

    从 YAML 文件加载配置并验证。
    """

    api: APIConfig
    aliyun: AliyunConfig | None = Field(default=None, description="阿里云通用凭证（可选）")
    devices: list[DeviceConfig] = Field(default_factory=list, description="设备列表")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="日志配置")
    oss: OSSConfig | None = Field(default=None, description="OSS 配置（可选）")

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
