"""
配置管理模块

从环境变量和 .env 文件中读取配置。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
# 项目根目录下的 .env 文件
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path=dotenv_path)


def get_data_base_path() -> Path:
    """
    获取数据存储基础路径

    优先级:
    1. 环境变量 BASE_URL (从 .env 文件或系统环境变量)
    2. 默认值: 项目根目录下的 data 路径

    Returns:
        数据存储基础路径
    """
    base_url = os.getenv("BASE_URL")

    if base_url:
        # 如果环境变量存在，使用环境变量指定的路径
        base_path = Path(base_url)
        if not base_path.is_absolute():
            return project_root / base_path
        return base_path
    else:
        # 否则使用默认路径: 项目根目录下的 data
        return project_root / "data"


def get_messages_raw_path() -> Path:
    """
    获取原始消息存储路径 (JSONL)

    Returns:
        原始消息存储路径 (data/messages/raw)
    """
    base_path = get_data_base_path()
    return base_path / "messages" / "raw"


def get_messages_parquet_path() -> Path:
    """
    获取 Parquet 消息存储路径

    Returns:
        Parquet 消息存储路径 (data/messages/parquet)
    """
    base_path = get_data_base_path()
    return base_path / "messages" / "parquet"


def get_llm_config_path() -> Path:
    """
    获取 LLM 配置文件路径

    Returns:
        LLM 配置文件路径 (config/llm.yaml)
    """
    return project_root / "config" / "llm.yaml"


def get_images_db_path() -> Path:
    """获取图片元数据数据库路径

    Returns:
        图片数据库路径 (data/metadata/images.duckdb)
    """
    base_path = get_data_base_path()
    return base_path / "metadata" / "images.duckdb"


def get_deepseek_api_key() -> str:
    """
    获取 DeepSeek API Key

    Returns:
        DeepSeek API Key

    Raises:
        ValueError: 如果环境变量 DEEPSEEK_API_KEY 未设置
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY not found in environment variables. "
            "Please set it in .env file or system environment."
        )
    return api_key
