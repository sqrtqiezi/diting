"""VectorStore Protocol 测试

TDD RED Phase: 先写测试，验证 Protocol 接口设计。
"""


class TestVectorStoreProtocol:
    """VectorStore Protocol 测试"""

    def test_protocol_has_upsert_method(self):
        """测试 Protocol 定义了 upsert 方法"""
        from diting.services.llm.vector_store.store import VectorStore

        assert hasattr(VectorStore, "upsert")

    def test_protocol_has_search_similar_method(self):
        """测试 Protocol 定义了 search_similar 方法"""
        from diting.services.llm.vector_store.store import VectorStore

        assert hasattr(VectorStore, "search_similar")

    def test_protocol_has_get_embeddings_method(self):
        """测试 Protocol 定义了 get_embeddings 方法"""
        from diting.services.llm.vector_store.store import VectorStore

        assert hasattr(VectorStore, "get_embeddings")


class MockVectorStore:
    """Mock 向量存储用于测试 Protocol 兼容性"""

    def __init__(self):
        self._storage: dict[str, dict] = {}

    def upsert(
        self,
        chatroom_id: str,
        messages: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """插入或更新向量"""
        for msg, emb in zip(messages, embeddings, strict=False):
            key = f"{chatroom_id}:{msg['msg_id']}"
            self._storage[key] = {
                "msg_id": msg["msg_id"],
                "chatroom_id": chatroom_id,
                "content": msg.get("content", ""),
                "embedding": emb,
            }

    def search_similar(
        self,
        query_embedding: list[float],
        chatroom_id: str | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """相似性搜索"""
        results = []
        for _, item in self._storage.items():
            if chatroom_id and item["chatroom_id"] != chatroom_id:
                continue
            # 简单的余弦相似度模拟
            score = sum(a * b for a, b in zip(query_embedding, item["embedding"], strict=False))
            results.append(
                {
                    "msg_id": item["msg_id"],
                    "content": item["content"],
                    "score": score,
                }
            )
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get_embeddings(
        self,
        chatroom_id: str,
        message_ids: list[str],
    ) -> list[list[float]]:
        """获取指定消息的向量"""
        embeddings = []
        for msg_id in message_ids:
            key = f"{chatroom_id}:{msg_id}"
            if key in self._storage:
                embeddings.append(self._storage[key]["embedding"])
        return embeddings


class TestMockVectorStoreCompliance:
    """测试 Mock Store 符合 Protocol"""

    def test_mock_store_is_protocol_compliant(self):
        """测试 Mock Store 符合 VectorStore Protocol"""
        store = MockVectorStore()

        # 验证方法存在且可调用
        assert callable(store.upsert)
        assert callable(store.search_similar)
        assert callable(store.get_embeddings)

    def test_upsert_stores_data(self):
        """测试 upsert 存储数据"""
        store = MockVectorStore()
        messages = [
            {"msg_id": "msg_001", "content": "hello"},
            {"msg_id": "msg_002", "content": "world"},
        ]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]

        store.upsert("chatroom_1", messages, embeddings)

        # 验证数据已存储
        assert len(store._storage) == 2

    def test_search_similar_returns_results(self):
        """测试 search_similar 返回结果"""
        store = MockVectorStore()
        messages = [
            {"msg_id": "msg_001", "content": "hello"},
            {"msg_id": "msg_002", "content": "world"},
        ]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        store.upsert("chatroom_1", messages, embeddings)

        results = store.search_similar([0.1, 0.2], chatroom_id="chatroom_1", top_k=2)

        assert len(results) == 2
        assert "msg_id" in results[0]
        assert "content" in results[0]
        assert "score" in results[0]

    def test_search_similar_filters_by_chatroom(self):
        """测试 search_similar 按 chatroom 过滤"""
        store = MockVectorStore()
        store.upsert("chatroom_1", [{"msg_id": "msg_001", "content": "hello"}], [[0.1, 0.2]])
        store.upsert("chatroom_2", [{"msg_id": "msg_002", "content": "world"}], [[0.3, 0.4]])

        results = store.search_similar([0.1, 0.2], chatroom_id="chatroom_1", top_k=10)

        assert len(results) == 1
        assert results[0]["msg_id"] == "msg_001"

    def test_get_embeddings_returns_vectors(self):
        """测试 get_embeddings 返回向量"""
        store = MockVectorStore()
        messages = [
            {"msg_id": "msg_001", "content": "hello"},
            {"msg_id": "msg_002", "content": "world"},
        ]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        store.upsert("chatroom_1", messages, embeddings)

        result = store.get_embeddings("chatroom_1", ["msg_001", "msg_002"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2]
        assert result[1] == [0.3, 0.4]

    def test_get_embeddings_handles_missing_ids(self):
        """测试 get_embeddings 处理不存在的 ID"""
        store = MockVectorStore()
        store.upsert("chatroom_1", [{"msg_id": "msg_001", "content": "hello"}], [[0.1, 0.2]])

        result = store.get_embeddings("chatroom_1", ["msg_001", "msg_999"])

        # 只返回存在的向量
        assert len(result) == 1
