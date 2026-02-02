"""OpenAI 兼容 Embedding Provider 测试

TDD RED Phase: 先写测试，验证 OpenAI Embedding 实现。
"""

from unittest.mock import MagicMock, patch


class TestOpenAIEmbeddingProvider:
    """OpenAI Embedding Provider 测试"""

    def test_import_openai_provider(self):
        """测试可以导入 OpenAIEmbeddingProvider"""
        from diting.services.llm.embedding.openai_provider import OpenAIEmbeddingProvider

        assert OpenAIEmbeddingProvider is not None

    def test_default_parameters(self):
        """测试默认参数"""
        from diting.services.llm.embedding.openai_provider import OpenAIEmbeddingProvider

        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        )

        assert provider.model == "text-embedding-3-small"
        assert provider.dimension == 1536
        assert provider.batch_size == 100

    def test_custom_parameters(self):
        """测试自定义参数"""
        from diting.services.llm.embedding.openai_provider import OpenAIEmbeddingProvider

        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            base_url="https://api.deepseek.com/v1",
            model="text-embedding-ada-002",
            dimension=768,
            batch_size=50,
        )

        assert provider.model == "text-embedding-ada-002"
        assert provider.dimension == 768
        assert provider.batch_size == 50

    def test_dimension_property(self):
        """测试 dimension 属性"""
        from diting.services.llm.embedding.openai_provider import OpenAIEmbeddingProvider

        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            dimension=1024,
        )

        assert provider.dimension == 1024

    @patch("diting.services.llm.embedding.openai_provider.OpenAI")
    def test_embed_documents_calls_api(self, mock_openai_class):
        """测试 embed_documents 调用 API"""
        from diting.services.llm.embedding.openai_provider import OpenAIEmbeddingProvider

        # 设置 mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6]),
        ]
        mock_client.embeddings.create.return_value = mock_response

        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            dimension=3,
        )

        result = provider.embed_documents(["hello", "world"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]
        mock_client.embeddings.create.assert_called_once()

    @patch("diting.services.llm.embedding.openai_provider.OpenAI")
    def test_embed_query_calls_api(self, mock_openai_class):
        """测试 embed_query 调用 API"""
        from diting.services.llm.embedding.openai_provider import OpenAIEmbeddingProvider

        # 设置 mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response

        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            dimension=3,
        )

        result = provider.embed_query("hello")

        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once()

    @patch("diting.services.llm.embedding.openai_provider.OpenAI")
    def test_embed_documents_handles_empty_input(self, mock_openai_class):
        """测试 embed_documents 处理空输入"""
        from diting.services.llm.embedding.openai_provider import OpenAIEmbeddingProvider

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        )

        result = provider.embed_documents([])

        assert result == []
        mock_client.embeddings.create.assert_not_called()

    @patch("diting.services.llm.embedding.openai_provider.OpenAI")
    def test_embed_documents_batches_large_input(self, mock_openai_class):
        """测试 embed_documents 对大量输入进行批处理"""
        from diting.services.llm.embedding.openai_provider import OpenAIEmbeddingProvider

        # 设置 mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        def create_response(input, **kwargs):
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 3) for _ in input]
            return mock_response

        mock_client.embeddings.create.side_effect = create_response

        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            dimension=3,
            batch_size=2,  # 小批次用于测试
        )

        # 5 个文本，batch_size=2，应该调用 3 次
        texts = ["text1", "text2", "text3", "text4", "text5"]
        result = provider.embed_documents(texts)

        assert len(result) == 5
        assert mock_client.embeddings.create.call_count == 3


class TestOpenAIEmbeddingProviderProtocolCompliance:
    """测试 OpenAI Provider 符合 EmbeddingProvider Protocol"""

    @patch("diting.services.llm.embedding.openai_provider.OpenAI")
    def test_implements_embedding_provider_protocol(self, mock_openai_class):
        """测试实现 EmbeddingProvider Protocol"""
        from diting.services.llm.embedding.openai_provider import OpenAIEmbeddingProvider

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        )

        # 验证方法存在且可调用
        assert callable(provider.embed_documents)
        assert callable(provider.embed_query)
        assert isinstance(provider.dimension, int)
