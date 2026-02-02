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

    max_content_length: int | None = Field(default=None, ge=1, description="单条消息最大长度")
    enable_xml_parsing: bool = Field(default=True, description="启用引用消息解析")
    enable_refermsg_display: bool = Field(default=True, description="提示词中展示引用消息")
    keyword_merge_threshold: float = Field(
        default=0.4, ge=0.0, le=1.0, description="关键词相似度合并阈值"
    )
    timezone: str = Field(default="UTC", description="报告显示时区 (如 Asia/Shanghai, UTC)")
    enable_image_ocr_display: bool = Field(default=True, description="启用图片 OCR 内容替换")

    model_config = {"extra": "ignore"}


class EmbeddingConfig(BaseModel):
    """Embedding 配置"""

    enabled: bool = Field(default=False, description="是否启用 Embedding 功能")
    provider: str = Field(default="openai", description="Embedding 服务商 (openai)")
    base_url: str = Field(default="https://api.openai.com/v1", description="API 基础 URL")
    api_key: str | None = Field(default=None, description="API Key (可通过环境变量设置)")
    model: str = Field(default="text-embedding-3-small", description="Embedding 模型名称")
    dimension: int = Field(default=1536, ge=1, description="向量维度")
    batch_size: int = Field(default=100, ge=1, le=2048, description="批处理大小")
    timeout: float = Field(default=60.0, ge=1.0, le=300.0, description="请求超时(秒)")


class ClusteringConfig(BaseModel):
    """聚类配置"""

    min_cluster_size: int = Field(default=5, ge=2, description="最小聚类大小")
    min_samples: int = Field(default=2, ge=1, description="核心点最小邻居数")
    metric: str = Field(default="euclidean", description="距离度量方式")


class VectorStoreConfig(BaseModel):
    """向量存储配置"""

    db_path: str = Field(default="data/vectors.duckdb", description="DuckDB 数据库路径")
    dimension: int = Field(default=1536, ge=1, description="向量维度 (应与 Embedding 一致)")


class ThreadingConfig(BaseModel):
    """话题线程切分配置"""

    enabled: bool = Field(default=False, description="是否启用话题线程切分")
    time_window_minutes: int = Field(default=30, ge=0, description="线程活跃时间窗口(分钟)")
    similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="线程归属相似度阈值"
    )
    reply_boost: float = Field(default=0.1, ge=0.0, le=1.0, description="引用/提及时的相似度提升")
    min_thread_size: int = Field(default=3, ge=1, description="最小线程消息数")


class LLMConfig(BaseModel):
    """LLM 配置"""

    api: APIConfig
    model_params: ModelParamsConfig = Field(default_factory=ModelParamsConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    clustering: ClusteringConfig = Field(default_factory=ClusteringConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    threading: ThreadingConfig = Field(default_factory=ThreadingConfig)

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

        # 处理 LLM API Key
        api_key = None
        if isinstance(config_data, dict):
            api_key = config_data.get("api", {}).get("api_key")
        if not api_key:
            # 按优先级尝试多个环境变量
            env_vars = [
                "LLM_API_KEY",
                "DASHSCOPE_API_KEY",
                "QWEN_API_KEY",
                "DEEPSEEK_API_KEY",
                "OPENAI_API_KEY",
            ]
            for env_var in env_vars:
                api_key = os.getenv(env_var)
                if api_key:
                    break
            if not api_key:
                raise ValueError(
                    "Missing LLM API key. Set one of: LLM_API_KEY, DASHSCOPE_API_KEY, "
                    "QWEN_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY, "
                    "or provide api.api_key in config/llm.yaml."
                )
            config_data.setdefault("api", {})["api_key"] = api_key

        # 处理 Embedding API Key
        if isinstance(config_data, dict):
            embedding_config = config_data.get("embedding", {})
            if embedding_config.get("enabled") and not embedding_config.get("api_key"):
                # 尝试从环境变量获取
                for env_var in ["EMBEDDING_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY"]:
                    embedding_api_key = os.getenv(env_var)
                    if embedding_api_key:
                        config_data.setdefault("embedding", {})["api_key"] = embedding_api_key
                        break

        return cls(**config_data)
