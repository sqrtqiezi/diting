"""LLM 配置加载模块"""

import os
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field


class TimeoutConfig(BaseModel):
    """超时配置"""

    connect: int = Field(default=30, ge=1, le=120, description="连接超时(秒)")
    read: int = Field(default=120, ge=1, le=600, description="读取超时(秒)")


class RetryConfig(BaseModel):
    """重试配置"""

    max_attempts: int = Field(default=3, ge=1, le=10, description="最大重试次数")
    backoff_factor: float = Field(default=1.0, ge=0, le=10.0, description="退避因子")


class APIConfig(BaseModel):
    """API 配置"""

    provider: str = Field(default="deepseek", description="LLM 服务商")
    base_url: str = Field(..., description="API 基础 URL")
    api_key: str | None = Field(default=None, description="API Key")
    model: str = Field(..., description="模型名称")
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig, description="超时配置")
    retry: RetryConfig = Field(default_factory=RetryConfig, description="重试配置")


class ModelParamsConfig(BaseModel):
    """模型参数配置"""

    temperature: float = Field(default=0.7, ge=0, le=2.0, description="采样温度")
    max_tokens: int = Field(default=2000, ge=1, description="最大输出 token 数")
    top_p: float = Field(default=0.95, ge=0, le=1.0, description="Top-p 采样")


class AnalysisConfig(BaseModel):
    """分析任务配置"""

    max_messages_per_batch: int | None = Field(default=None, ge=1, description="单次输入最大消息数")
    max_content_length: int | None = Field(default=None, ge=1, description="单条消息最大长度")
    enable_xml_parsing: bool = Field(default=True, description="启用引用消息解析")
    enable_refermsg_display: bool = Field(default=True, description="提示词中展示引用消息")
    prompt_version: str = Field(default="v1", description="提示词版本(v1/v2)")
    keyword_merge_threshold: float = Field(
        default=0.4, ge=0.0, le=1.0, description="关键词相似度合并阈值"
    )
    summary_max_tokens: int | None = Field(
        default=60000, ge=1000, description="单个话题摘要最大 token 预算"
    )
    summary_max_messages: int | None = Field(
        default=200, ge=1, description="单个话题摘要最大消息数"
    )
    timezone: str = Field(default="UTC", description="报告显示时区 (如 Asia/Shanghai, UTC)")
    enable_image_ocr_display: bool = Field(default=True, description="启用图片 OCR 内容替换")


class ClaudeCliConfig(BaseModel):
    """Claude CLI 配置"""

    enabled: bool = Field(default=False, description="是否启用 Claude CLI")
    model: str = Field(default="sonnet", description="模型名称 (sonnet/opus/haiku)")
    output_format: str = Field(
        default="json", description="输出格式 (text/json/stream-json)"
    )
    system_prompt: str | None = Field(default=None, description="系统提示词")
    max_budget_usd: float | None = Field(default=None, ge=0, description="最大预算(美元)")
    dangerously_skip_permissions: bool = Field(default=True, description="跳过权限检查")
    timeout: int = Field(default=300, ge=1, le=3600, description="超时时间(秒)")
    cli_path: str | None = Field(default=None, description="CLI 路径，None 则使用 PATH")


class LLMConfig(BaseModel):
    """LLM 配置"""

    api: APIConfig
    model_params: ModelParamsConfig = Field(default_factory=ModelParamsConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    claude_cli: ClaudeCliConfig = Field(default_factory=ClaudeCliConfig)

    model_config = {"extra": "ignore"}

    @classmethod
    def load_from_yaml(cls, config_path: str | Path) -> "LLMConfig":
        """从 YAML 文件加载配置"""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        try:
            with open(config_path, encoding="utf-8") as f:
                config_data: dict[str, Any] = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"无效的 YAML 格式: {e}") from e

        # claude-cli provider 不需要 API key
        provider = config_data.get("api", {}).get("provider", "deepseek").lower()
        if provider == "claude-cli":
            # 设置占位符以通过验证
            config_data.setdefault("api", {}).setdefault("api_key", "claude-cli-no-key")
            return cls(**config_data)

        api_key = None
        if isinstance(config_data, dict):
            api_key = config_data.get("api", {}).get("api_key")
        if not api_key:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError(
                    "Missing DeepSeek API key. Set DEEPSEEK_API_KEY in .env or "
                    "provide api.api_key in config/llm.yaml."
                )
            config_data.setdefault("api", {})["api_key"] = api_key
        return cls(**config_data)
