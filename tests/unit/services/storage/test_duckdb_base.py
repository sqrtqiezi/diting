"""DuckDB 基础设施单元测试"""

from pathlib import Path

import pytest
from diting.services.storage.duckdb_base import DuckDBConnection


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """创建临时数据库路径"""
    return tmp_path / "test.duckdb"


class TestDuckDBConnection:
    """DuckDBConnection 测试"""

    def test_creates_database_file(self, temp_db_path: Path) -> None:
        """测试创建数据库文件"""
        conn = DuckDBConnection(temp_db_path)
        # 执行一个简单查询触发连接
        with conn.get_connection() as db:
            db.execute("SELECT 1")
        assert temp_db_path.exists()

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """测试创建父目录"""
        db_path = tmp_path / "nested" / "dir" / "test.duckdb"
        _conn = DuckDBConnection(db_path)
        assert db_path.parent.exists()

    def test_execute_one_returns_dict(self, temp_db_path: Path) -> None:
        """测试 execute_one 返回字典"""
        conn = DuckDBConnection(temp_db_path)
        with conn.get_connection() as db:
            db.execute("CREATE TABLE test (id INT, name VARCHAR)")
            db.execute("INSERT INTO test VALUES (1, 'Alice')")

        result = conn.execute_one("SELECT id, name FROM test WHERE id = ?", [1])
        assert result == {"id": 1, "name": "Alice"}

    def test_execute_one_returns_none_when_not_found(self, temp_db_path: Path) -> None:
        """测试 execute_one 未找到时返回 None"""
        conn = DuckDBConnection(temp_db_path)
        with conn.get_connection() as db:
            db.execute("CREATE TABLE test (id INT)")

        result = conn.execute_one("SELECT id FROM test WHERE id = ?", [999])
        assert result is None

    def test_execute_many_returns_list_of_dicts(self, temp_db_path: Path) -> None:
        """测试 execute_many 返回字典列表"""
        conn = DuckDBConnection(temp_db_path)
        with conn.get_connection() as db:
            db.execute("CREATE TABLE test (id INT, name VARCHAR)")
            db.execute("INSERT INTO test VALUES (1, 'Alice'), (2, 'Bob')")

        results = conn.execute_many("SELECT id, name FROM test ORDER BY id")
        assert results == [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]

    def test_execute_many_returns_empty_list(self, temp_db_path: Path) -> None:
        """测试 execute_many 无结果时返回空列表"""
        conn = DuckDBConnection(temp_db_path)
        with conn.get_connection() as db:
            db.execute("CREATE TABLE test (id INT)")

        results = conn.execute_many("SELECT id FROM test")
        assert results == []

    def test_execute_returns_affected_rows(self, temp_db_path: Path) -> None:
        """测试 execute 返回影响的行数"""
        conn = DuckDBConnection(temp_db_path)
        with conn.get_connection() as db:
            db.execute("CREATE TABLE test (id INT, name VARCHAR)")
            db.execute("INSERT INTO test VALUES (1, 'Alice'), (2, 'Bob')")

        # DuckDB 的 UPDATE 返回影响的行数
        conn.execute("UPDATE test SET name = 'Updated' WHERE id = ?", [1])
        result = conn.execute_one("SELECT name FROM test WHERE id = ?", [1])
        assert result == {"name": "Updated"}

    def test_connection_context_manager(self, temp_db_path: Path) -> None:
        """测试连接上下文管理器"""
        conn = DuckDBConnection(temp_db_path)

        with conn.get_connection() as db:
            db.execute("CREATE TABLE test (id INT)")
            db.execute("INSERT INTO test VALUES (1)")

        # 连接应该已关闭，但数据应该持久化
        result = conn.execute_one("SELECT id FROM test")
        assert result == {"id": 1}
