"""
存储服务 CLI 命令包

提供查询、摄入、维护和检测等存储管理命令。

模块结构:
- query_commands: 消息查询命令 (query, query-by-id)
- ingestion_commands: 数据摄入命令 (dump-parquet, ingest-message)
- maintenance_commands: 维护命令 (validate, cleanup, archive)
- detect_commands: 检测命令 (detect-duplicates)
- utils: 公共工具 (装饰器、输出格式化、退出码)
"""

import click

from .detect_commands import detect_duplicates_cmd
from .ingestion_commands import dump_parquet, ingest_message
from .maintenance_commands import archive, cleanup, validate
from .query_commands import query, query_by_id
from .utils import ExitCode, Output


@click.group()
def storage() -> None:
    """存储服务管理命令"""
    pass


# 注册所有命令
storage.add_command(query)
storage.add_command(query_by_id)
storage.add_command(dump_parquet)
storage.add_command(ingest_message)
storage.add_command(validate)
storage.add_command(cleanup)
storage.add_command(archive)
storage.add_command(detect_duplicates_cmd, name="detect-duplicates")


__all__ = [
    "storage",
    "query",
    "query_by_id",
    "dump_parquet",
    "ingest_message",
    "validate",
    "cleanup",
    "archive",
    "detect_duplicates_cmd",
    "ExitCode",
    "Output",
]
