"""
存储服务 CLI 命令 (兼容层)

此模块为向后兼容保留，实际实现已迁移到 src/cli/storage/ 包。

重构后的模块结构:
- src/cli/storage/query_commands.py: 查询命令 (query, query-by-id)
- src/cli/storage/ingestion_commands.py: 摄入命令 (dump-parquet, ingest-message)
- src/cli/storage/maintenance_commands.py: 维护命令 (validate, cleanup, archive)
- src/cli/storage/detect_commands.py: 检测命令 (detect-duplicates)
- src/cli/storage/utils.py: 公共工具
"""

# 从新模块导入所有命令
from diting.cli.storage import (
    archive,
    cleanup,
    detect_duplicates_cmd,
    dump_parquet,
    ingest_message,
    query,
    query_by_id,
    storage,
    validate,
)

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
]

if __name__ == "__main__":
    storage()
