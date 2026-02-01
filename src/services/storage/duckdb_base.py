"""DuckDB 基础设施模块

提供数据库连接管理和基础查询执行功能。
"""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb
import structlog

logger = structlog.get_logger()


class DuckDBConnection:
    """DuckDB 连接管理器

    提供数据库连接和基础查询执行功能。
    """

    def __init__(self, db_path: Path | str) -> None:
        """初始化连接管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """获取数据库连接

        使用上下文管理器确保连接正确关闭。

        Yields:
            DuckDB 连接对象
        """
        conn = duckdb.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, sql: str, params: list[Any] | None = None) -> None:
        """执行 SQL 语句

        Args:
            sql: SQL 语句
            params: 参数列表
        """
        with self.get_connection() as conn:
            conn.execute(sql, params or [])

    def execute_one(self, sql: str, params: list[Any] | None = None) -> dict[str, Any] | None:
        """执行查询并返回单条记录

        Args:
            sql: SQL 查询语句
            params: 参数列表

        Returns:
            记录字典，不存在返回 None
        """
        with self.get_connection() as conn:
            result = conn.execute(sql, params or []).fetchone()
            if not result:
                return None
            columns = [desc[0] for desc in conn.description]
            return dict(zip(columns, result, strict=False))

    def execute_many(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """执行查询并返回多条记录

        Args:
            sql: SQL 查询语句
            params: 参数列表

        Returns:
            记录字典列表
        """
        with self.get_connection() as conn:
            results = conn.execute(sql, params or []).fetchall()
            if not results:
                return []
            columns = [desc[0] for desc in conn.description]
            return [dict(zip(columns, row, strict=False)) for row in results]
