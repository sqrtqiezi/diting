"""结构化日志配置

使用 structlog 和 orjson 实现高性能 JSON 日志记录。
"""

import logging
import sys
from datetime import UTC
from pathlib import Path
from typing import Any

import orjson
import structlog
from structlog.types import EventDict, Processor


def orjson_dumps(obj: Any, **kwargs: Any) -> bytes:
    """使用 orjson 序列化 JSON

    orjson 比标准库 json 快 2-3 倍。

    Args:
        obj: 要序列化的对象
        **kwargs: 传递给 orjson.dumps 的额外参数(被忽略)

    Returns:
        bytes: JSON 字节串
    """
    return orjson.dumps(obj)


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """添加 ISO 8601 格式的时间戳

    Args:
        logger: 日志记录器(未使用)
        method_name: 日志方法名称(未使用)
        event_dict: 事件字典

    Returns:
        EventDict: 添加了 timestamp 字段的事件字典
    """
    from datetime import datetime

    event_dict["timestamp"] = datetime.now(UTC).isoformat()
    return event_dict


def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """添加日志级别字段

    Args:
        logger: 日志记录器(未使用)
        method_name: 日志方法名称
        event_dict: 事件字典

    Returns:
        EventDict: 添加了 level 字段的事件字典
    """
    if method_name == "warn":
        method_name = "warning"
    event_dict["level"] = method_name.upper()
    return event_dict


def configure_logging(
    level: str = "INFO",
    log_file: str | None = None,
    json_format: bool = True,
) -> None:
    """配置全局日志系统

    Args:
        level: 日志级别(DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_file: 日志文件路径(可选),None 表示仅输出到控制台
        json_format: 是否使用 JSON 格式(True)或人类可读格式(False)
    """
    # 导入敏感数据脱敏处理器
    from diting.utils.security import mask_sensitive_data

    # 配置处理器链
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_timestamp,
        add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        mask_sensitive_data,  # 自动脱敏敏感字段
    ]

    if json_format:
        # JSON 格式 - 生产环境
        processors.append(
            structlog.processors.JSONRenderer(serializer=lambda obj, **kwargs: orjson_dumps(obj))
        )
    else:
        # 人类可读格式 - 开发环境
        processors.append(structlog.dev.ConsoleRenderer())

    # 配置 structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 配置标准库 logging(供第三方库使用)
    logging.basicConfig(
        format="%(message)s",
        level=level.upper(),
        stream=sys.stdout,
    )

    # 如果指定了日志文件,添加文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(level.upper())
        logging.root.addHandler(file_handler)


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """获取结构化日志记录器

    Args:
        name: 日志记录器名称(可选),通常使用模块名 __name__

    Returns:
        structlog.BoundLogger: 结构化日志记录器
    """
    return structlog.get_logger(name)
