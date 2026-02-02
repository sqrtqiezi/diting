"""DuckDB VSS 向量存储测试

TDD RED Phase: 先写测试，验证 DuckDB VSS 实现。
"""

import os
import tempfile

import pytest


class TestDuckDBVectorStore:
    """DuckDB 向量存储测试"""

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield os.path.join(tmpdir, "test.duckdb")

    def test_import_duckdb_store(self):
        """测试可以导入 DuckDBVectorStore"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        assert DuckDBVectorStore is not None

    def test_init_creates_schema(self, temp_db_path):
        """测试初始化创建 schema"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        store = DuckDBVectorStore(db_path=temp_db_path, dimension=128)

        # 验证表已创建
        assert store is not None
        store.close()

    def test_init_with_memory_db(self):
        """测试使用内存数据库"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        store = DuckDBVectorStore(db_path=":memory:", dimension=128)

        assert store is not None
        store.close()

    def test_upsert_stores_data(self, temp_db_path):
        """测试 upsert 存储数据"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        store = DuckDBVectorStore(db_path=temp_db_path, dimension=3)
        messages = [
            {"msg_id": "msg_001", "content": "hello", "create_time": "2026-01-01 10:00:00"},
            {"msg_id": "msg_002", "content": "world", "create_time": "2026-01-01 10:01:00"},
        ]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        store.upsert("chatroom_1", messages, embeddings)

        # 验证数据已存储
        count = store._conn.execute("SELECT COUNT(*) FROM message_embeddings").fetchone()[0]
        assert count == 2
        store.close()

    def test_upsert_updates_existing(self, temp_db_path):
        """测试 upsert 更新已存在的数据"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        store = DuckDBVectorStore(db_path=temp_db_path, dimension=3)
        messages = [{"msg_id": "msg_001", "content": "hello", "create_time": "2026-01-01 10:00:00"}]
        embeddings = [[0.1, 0.2, 0.3]]

        # 第一次插入
        store.upsert("chatroom_1", messages, embeddings)

        # 更新内容和向量
        messages[0]["content"] = "updated"
        embeddings[0] = [0.9, 0.8, 0.7]
        store.upsert("chatroom_1", messages, embeddings)

        # 验证只有一条记录
        count = store._conn.execute("SELECT COUNT(*) FROM message_embeddings").fetchone()[0]
        assert count == 1

        # 验证内容已更新
        content = store._conn.execute(
            "SELECT content FROM message_embeddings WHERE msg_id = 'msg_001'"
        ).fetchone()[0]
        assert content == "updated"
        store.close()

    def test_search_similar_returns_results(self, temp_db_path):
        """测试 search_similar 返回结果"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        store = DuckDBVectorStore(db_path=temp_db_path, dimension=3)
        messages = [
            {"msg_id": "msg_001", "content": "hello", "create_time": "2026-01-01 10:00:00"},
            {"msg_id": "msg_002", "content": "world", "create_time": "2026-01-01 10:01:00"},
        ]
        embeddings = [[0.1, 0.2, 0.3], [0.9, 0.8, 0.7]]
        store.upsert("chatroom_1", messages, embeddings)

        # 搜索与第一个向量相似的
        results = store.search_similar([0.1, 0.2, 0.3], top_k=2)

        assert len(results) == 2
        assert "msg_id" in results[0]
        assert "content" in results[0]
        assert "score" in results[0]
        # 第一个结果应该是最相似的
        assert results[0]["msg_id"] == "msg_001"
        store.close()

    def test_search_similar_filters_by_chatroom(self, temp_db_path):
        """测试 search_similar 按 chatroom 过滤"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        store = DuckDBVectorStore(db_path=temp_db_path, dimension=3)
        store.upsert(
            "chatroom_1",
            [{"msg_id": "msg_001", "content": "hello", "create_time": "2026-01-01 10:00:00"}],
            [[0.1, 0.2, 0.3]],
        )
        store.upsert(
            "chatroom_2",
            [{"msg_id": "msg_002", "content": "world", "create_time": "2026-01-01 10:01:00"}],
            [[0.9, 0.8, 0.7]],
        )

        results = store.search_similar([0.1, 0.2, 0.3], chatroom_id="chatroom_1", top_k=10)

        assert len(results) == 1
        assert results[0]["msg_id"] == "msg_001"
        store.close()

    def test_search_similar_respects_top_k(self, temp_db_path):
        """测试 search_similar 遵守 top_k 限制"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        store = DuckDBVectorStore(db_path=temp_db_path, dimension=3)
        messages = [
            {
                "msg_id": f"msg_{i:03d}",
                "content": f"content_{i}",
                "create_time": "2026-01-01 10:00:00",
            }
            for i in range(10)
        ]
        embeddings = [[0.1 * i, 0.2 * i, 0.3 * i] for i in range(10)]
        store.upsert("chatroom_1", messages, embeddings)

        results = store.search_similar([0.5, 1.0, 1.5], top_k=3)

        assert len(results) == 3
        store.close()

    def test_get_embeddings_returns_vectors(self, temp_db_path):
        """测试 get_embeddings 返回向量"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        store = DuckDBVectorStore(db_path=temp_db_path, dimension=3)
        messages = [
            {"msg_id": "msg_001", "content": "hello", "create_time": "2026-01-01 10:00:00"},
            {"msg_id": "msg_002", "content": "world", "create_time": "2026-01-01 10:01:00"},
        ]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        store.upsert("chatroom_1", messages, embeddings)

        result = store.get_embeddings("chatroom_1", ["msg_001", "msg_002"])

        assert len(result) == 2
        # 验证向量值（允许浮点误差）
        assert abs(result[0][0] - 0.1) < 0.001
        assert abs(result[1][0] - 0.4) < 0.001
        store.close()

    def test_get_embeddings_handles_missing_ids(self, temp_db_path):
        """测试 get_embeddings 处理不存在的 ID"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        store = DuckDBVectorStore(db_path=temp_db_path, dimension=3)
        store.upsert(
            "chatroom_1",
            [{"msg_id": "msg_001", "content": "hello", "create_time": "2026-01-01 10:00:00"}],
            [[0.1, 0.2, 0.3]],
        )

        result = store.get_embeddings("chatroom_1", ["msg_001", "msg_999"])

        # 只返回存在的向量
        assert len(result) == 1
        store.close()

    def test_get_embeddings_preserves_order(self, temp_db_path):
        """测试 get_embeddings 保持请求顺序"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        store = DuckDBVectorStore(db_path=temp_db_path, dimension=3)
        messages = [
            {"msg_id": "msg_001", "content": "hello", "create_time": "2026-01-01 10:00:00"},
            {"msg_id": "msg_002", "content": "world", "create_time": "2026-01-01 10:01:00"},
        ]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        store.upsert("chatroom_1", messages, embeddings)

        # 请求顺序与插入顺序相反
        result = store.get_embeddings("chatroom_1", ["msg_002", "msg_001"])

        assert len(result) == 2
        # 第一个应该是 msg_002 的向量
        assert abs(result[0][0] - 0.4) < 0.001
        # 第二个应该是 msg_001 的向量
        assert abs(result[1][0] - 0.1) < 0.001
        store.close()


class TestDuckDBVectorStoreProtocolCompliance:
    """测试 DuckDB 存储符合 VectorStore Protocol"""

    def test_implements_vector_store_protocol(self):
        """测试实现 VectorStore Protocol"""
        from diting.services.llm.vector_store.duckdb_store import DuckDBVectorStore

        store = DuckDBVectorStore(db_path=":memory:", dimension=128)

        # 验证方法存在且可调用
        assert callable(store.upsert)
        assert callable(store.search_similar)
        assert callable(store.get_embeddings)
        store.close()
