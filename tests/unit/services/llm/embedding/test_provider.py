"""EmbeddingProvider Protocol 测试

TDD RED Phase: 先写测试，验证 Protocol 接口设计。
"""


class TestEmbeddingProviderProtocol:
    """EmbeddingProvider Protocol 测试"""

    def test_protocol_has_embed_documents_method(self):
        """测试 Protocol 定义了 embed_documents 方法"""
        from diting.services.llm.embedding.provider import EmbeddingProvider

        # Protocol 应该定义 embed_documents 方法
        assert hasattr(EmbeddingProvider, "embed_documents")

    def test_protocol_has_embed_query_method(self):
        """测试 Protocol 定义了 embed_query 方法"""
        from diting.services.llm.embedding.provider import EmbeddingProvider

        # Protocol 应该定义 embed_query 方法
        assert hasattr(EmbeddingProvider, "embed_query")

    def test_protocol_has_dimension_property(self):
        """测试 Protocol 定义了 dimension 属性"""
        from diting.services.llm.embedding.provider import EmbeddingProvider

        # Protocol 应该定义 dimension 属性
        assert hasattr(EmbeddingProvider, "dimension")


class MockEmbeddingProvider:
    """Mock Embedding Provider 用于测试 Protocol 兼容性"""

    def __init__(self, dimension: int = 1024):
        self._dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文档"""
        return [[0.1] * self._dimension for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        """嵌入查询"""
        return [0.1] * self._dimension

    @property
    def dimension(self) -> int:
        """向量维度"""
        return self._dimension


class TestMockEmbeddingProviderCompliance:
    """测试 Mock Provider 符合 Protocol"""

    def test_mock_provider_is_protocol_compliant(self):
        """测试 Mock Provider 符合 EmbeddingProvider Protocol"""

        provider = MockEmbeddingProvider(dimension=768)

        # 验证方法存在且可调用
        assert callable(provider.embed_documents)
        assert callable(provider.embed_query)
        assert isinstance(provider.dimension, int)

    def test_embed_documents_returns_correct_shape(self):
        """测试 embed_documents 返回正确的形状"""
        provider = MockEmbeddingProvider(dimension=768)
        texts = ["hello", "world"]

        embeddings = provider.embed_documents(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 768
        assert len(embeddings[1]) == 768

    def test_embed_query_returns_correct_shape(self):
        """测试 embed_query 返回正确的形状"""
        provider = MockEmbeddingProvider(dimension=768)

        embedding = provider.embed_query("hello")

        assert len(embedding) == 768

    def test_dimension_property(self):
        """测试 dimension 属性"""
        provider = MockEmbeddingProvider(dimension=1024)

        assert provider.dimension == 1024
