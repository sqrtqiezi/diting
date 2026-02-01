"""
存储命令公共工具

提供装饰器和输出格式化工具，用于统一 CLI 命令的行为。
"""

from collections.abc import Callable
from enum import IntEnum
from functools import wraps
from typing import Any, TypeVar

import click
import structlog

logger = structlog.get_logger()

F = TypeVar("F", bound=Callable[..., Any])


class ExitCode(IntEnum):
    """CLI 命令退出码

    遵循 Unix 退出码约定和 BSD sysexits.h 标准：
    - 0: 成功
    - 1: 一般错误
    - 2: 参数/用法错误
    - 64-78: BSD sysexits.h 标准错误码
    - 130: 用户中断 (SIGINT, Ctrl+C)

    使用示例:
        sys.exit(ExitCode.SUCCESS)
        sys.exit(ExitCode.FILE_NOT_FOUND)
    """

    # === 成功 ===
    SUCCESS = 0  # 命令执行成功

    # === 一般错误 ===
    GENERAL_ERROR = 1  # 未分类的一般错误（兜底）

    # === 参数/配置错误 ===
    INVALID_ARGUMENT = 2  # 命令行参数错误、参数冲突
    CONFIG_ERROR = 78  # 配置文件不存在或格式错误 (EX_CONFIG)

    # === 数据错误 ===
    DATA_ERROR = 65  # 数据格式错误，如 JSON 解析失败 (EX_DATAERR)
    VALIDATION_FAILED = 3  # 数据验证失败（如发现重复、分区无效）

    # === 资源错误 ===
    FILE_NOT_FOUND = 66  # 文件或目录不存在 (EX_NOINPUT)
    PERMISSION_DENIED = 77  # 权限不足 (EX_NOPERM)
    IO_ERROR = 74  # 文件系统 IO 错误 (EX_IOERR)

    # === 外部服务错误 ===
    NETWORK_ERROR = 69  # 网络连接失败 (EX_UNAVAILABLE)
    API_ERROR = 76  # 远程 API 调用失败 (EX_PROTOCOL)

    # === 用户中断 ===
    USER_INTERRUPTED = 130  # 用户手工中断 (128 + SIGINT=2)


def with_parquet_root(func: F) -> F:
    """自动解析 parquet_root 参数

    如果 parquet_root 为 None，则从配置中读取默认路径。
    """

    @wraps(func)
    def wrapper(*args: Any, parquet_root: str | None = None, **kwargs: Any) -> Any:
        if parquet_root is None:
            from src.config import get_messages_parquet_path

            parquet_root = str(get_messages_parquet_path())
        return func(*args, parquet_root=parquet_root, **kwargs)

    return wrapper  # type: ignore[return-value]


def with_raw_dir(func: F) -> F:
    """自动解析 raw_dir 参数

    如果 raw_dir 为 None，则从配置中读取默认路径。
    """

    @wraps(func)
    def wrapper(*args: Any, raw_dir: str | None = None, **kwargs: Any) -> Any:
        if raw_dir is None:
            from src.config import get_messages_raw_path

            raw_dir = str(get_messages_raw_path())
        return func(*args, raw_dir=raw_dir, **kwargs)

    return wrapper  # type: ignore[return-value]


def handle_storage_errors(operation_name: str) -> Callable[[F], F]:
    """统一错误处理装饰器

    捕获异常并输出统一格式的错误信息，同时记录日志。

    Args:
        operation_name: 操作名称，用于日志记录
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except SystemExit:
                raise
            except Exception as e:
                click.echo(f"✗ {operation_name}失败: {e}", err=True)
                logger.exception(f"{operation_name}_failed", error=str(e))
                raise SystemExit(1) from e

        return wrapper  # type: ignore[return-value]

    return decorator


class Output:
    """统一输出格式化工具"""

    @staticmethod
    def success(message: str, **details: Any) -> None:
        """输出成功信息

        Args:
            message: 主要信息
            **details: 附加详情，以 key: value 格式显示
        """
        click.echo(f"✓ {message}")
        for key, value in details.items():
            click.echo(f"  {key}: {value}")

    @staticmethod
    def error(message: str) -> None:
        """输出错误信息"""
        click.echo(f"✗ {message}", err=True)

    @staticmethod
    def info(message: str) -> None:
        """输出普通信息"""
        click.echo(message)

    @staticmethod
    def warning(message: str) -> None:
        """输出警告信息"""
        click.echo(f"⚠ {message}")

    @staticmethod
    def separator(char: str = "=", width: int = 60) -> None:
        """输出分隔线"""
        click.echo(char * width)

    @staticmethod
    def table_row(label: str, value: Any, indent: int = 2) -> None:
        """输出表格行"""
        prefix = " " * indent
        click.echo(f"{prefix}{label}: {value}")
