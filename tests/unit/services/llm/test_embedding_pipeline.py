"""embedding_pipeline 模块单元测试

测试 EmbeddingClusterPipeline 的聚类流程。
"""

import pytest
from diting.services.llm.clustering import Cluster
from diting.services.llm.config import (
    AnalysisConfig,
    APIConfig,
    ClusteringConfig,
    EmbeddingConfig,
    LLMConfig,
    ModelParamsConfig,
)
from diting.services.llm.embedding_pipeline import ClusterResult, EmbeddingClusterPipeline


@pytest.fixture
def mock_config():
    """创建测试配置"""
    return LLMConfig(
        api=APIConfig(
            provider="test",
            base_url="https://api.test.com",
            api_key="test-key",
            model="test-model",
        ),
        model_params=ModelParamsConfig(),
        analysis=AnalysisConfig(),
        embedding=EmbeddingConfig(
            enabled=True,
            api_key="test-embedding-key",
            base_url="https://api.test.com",
            model="test-embedding-model",
            dimension=128,
        ),
        clustering=ClusteringConfig(
            min_cluster_size=2,
            min_samples=1,
        ),
    )


class MockEmbeddingProvider:
    """Mock Embedding 提供者"""

    def __init__(self, dimension: int = 128):
        self._dimension = dimension
        self.call_count = 0
        self.last_texts: list[str] = []

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """模拟 Embedding 调用，返回简单的向量"""
        self.call_count += 1
        self.last_texts = texts
        # 返回简单的向量，每个文本的向量是其索引的重复
        return [[float(i)] * self._dimension for i in range(len(texts))]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * self._dimension


class MockClusteringStrategy:
    """Mock 聚类策略"""

    def __init__(self, clusters: list[Cluster] | None = None):
        self.clusters = clusters or []
        self.call_count = 0
        self.last_embeddings: list[list[float]] = []
        self.last_message_ids: list[str] = []

    def cluster(
        self,
        embeddings: list[list[float]],
        message_ids: list[str],
    ) -> list[Cluster]:
        """模拟聚类调用"""
        self.call_count += 1
        self.last_embeddings = embeddings
        self.last_message_ids = message_ids

        if self.clusters:
            return self.clusters

        # 默认行为：所有消息归为一个聚类
        return [
            Cluster(
                cluster_id=0,
                message_ids=message_ids,
                centroid=[0.0] * len(embeddings[0]) if embeddings else None,
            )
        ]


class MockVectorStore:
    """Mock 向量存储"""

    def __init__(self):
        self.upsert_calls: list[tuple[str, list[dict], list[list[float]]]] = []

    def upsert(
        self,
        chatroom_id: str,
        messages: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        self.upsert_calls.append((chatroom_id, messages, embeddings))


class TestEmbeddingClusterPipeline:
    """EmbeddingClusterPipeline 测试"""

    def test_cluster_empty_messages(self, mock_config):
        """测试空消息列表"""
        mock_embedding = MockEmbeddingProvider()
        mock_clustering = MockClusteringStrategy()

        pipeline = EmbeddingClusterPipeline(
            config=mock_config,
            embedding_provider=mock_embedding,
            clustering_strategy=mock_clustering,
        )

        result = pipeline.cluster_messages("chatroom_001", [])

        assert result == []
        assert mock_embedding.call_count == 0
        assert mock_clustering.call_count == 0

    def test_cluster_messages_with_empty_content(self, mock_config):
        """测试所有消息内容为空（但 sender 不为空，所以文本不为空）"""
        mock_embedding = MockEmbeddingProvider()
        mock_clustering = MockClusteringStrategy()

        pipeline = EmbeddingClusterPipeline(
            config=mock_config,
            embedding_provider=mock_embedding,
            clustering_strategy=mock_clustering,
        )

        # 注意：即使 content 为空，_extract_texts 会生成 "user1: " 这样的文本
        # 这不是空字符串，所以会被处理
        messages = [
            {"msg_id": "msg_001", "content": "", "chatroom_sender": "user1"},
            {"msg_id": "msg_002", "content": "   ", "chatroom_sender": "user2"},
        ]

        result = pipeline.cluster_messages("chatroom_001", messages)

        # 由于 "user1: " 和 "user2:    " 不是空字符串，所以会被处理
        assert len(result) == 1
        assert mock_embedding.call_count == 1

    def test_cluster_messages_normal_flow(self, mock_config):
        """测试正常聚类流程"""
        mock_embedding = MockEmbeddingProvider(dimension=128)
        mock_clustering = MockClusteringStrategy()

        pipeline = EmbeddingClusterPipeline(
            config=mock_config,
            embedding_provider=mock_embedding,
            clustering_strategy=mock_clustering,
        )

        messages = [
            {"msg_id": "msg_001", "content": "Hello world", "chatroom_sender": "user1"},
            {"msg_id": "msg_002", "content": "Hi there", "chatroom_sender": "user2"},
            {"msg_id": "msg_003", "content": "Good morning", "chatroom_sender": "user1"},
        ]

        result = pipeline.cluster_messages("chatroom_001", messages)

        # 验证 Embedding 被调用
        assert mock_embedding.call_count == 1
        assert len(mock_embedding.last_texts) == 3
        assert "user1: Hello world" in mock_embedding.last_texts

        # 验证聚类被调用
        assert mock_clustering.call_count == 1
        assert len(mock_clustering.last_message_ids) == 3

        # 验证返回结果
        assert len(result) == 1
        assert result[0].cluster_id == 0
        assert len(result[0].message_ids) == 3
        assert len(result[0].messages) == 3

    def test_cluster_messages_with_multiple_clusters(self, mock_config):
        """测试多个聚类"""
        mock_embedding = MockEmbeddingProvider(dimension=128)

        # 预设两个聚类
        mock_clustering = MockClusteringStrategy(
            clusters=[
                Cluster(cluster_id=0, message_ids=["msg_001", "msg_002"], centroid=[0.0] * 128),
                Cluster(cluster_id=1, message_ids=["msg_003"], centroid=[1.0] * 128),
            ]
        )

        pipeline = EmbeddingClusterPipeline(
            config=mock_config,
            embedding_provider=mock_embedding,
            clustering_strategy=mock_clustering,
        )

        messages = [
            {"msg_id": "msg_001", "content": "Hello", "chatroom_sender": "user1"},
            {"msg_id": "msg_002", "content": "Hi", "chatroom_sender": "user2"},
            {"msg_id": "msg_003", "content": "Goodbye", "chatroom_sender": "user1"},
        ]

        result = pipeline.cluster_messages("chatroom_001", messages)

        assert len(result) == 2
        assert result[0].cluster_id == 0
        assert result[0].message_ids == ["msg_001", "msg_002"]
        assert result[1].cluster_id == 1
        assert result[1].message_ids == ["msg_003"]

    def test_cluster_messages_with_noise(self, mock_config):
        """测试包含噪声点的聚类"""
        mock_embedding = MockEmbeddingProvider(dimension=128)

        # 预设一个正常聚类和一个噪声点聚类
        mock_clustering = MockClusteringStrategy(
            clusters=[
                Cluster(cluster_id=-1, message_ids=["msg_001"], centroid=None),
                Cluster(cluster_id=0, message_ids=["msg_002", "msg_003"], centroid=[0.0] * 128),
            ]
        )

        pipeline = EmbeddingClusterPipeline(
            config=mock_config,
            embedding_provider=mock_embedding,
            clustering_strategy=mock_clustering,
        )

        messages = [
            {"msg_id": "msg_001", "content": "Random", "chatroom_sender": "user1"},
            {"msg_id": "msg_002", "content": "Hello", "chatroom_sender": "user2"},
            {"msg_id": "msg_003", "content": "Hi", "chatroom_sender": "user1"},
        ]

        result = pipeline.cluster_messages("chatroom_001", messages)

        assert len(result) == 2
        # 噪声点聚类
        noise_cluster = next(r for r in result if r.cluster_id == -1)
        assert noise_cluster.message_ids == ["msg_001"]
        assert noise_cluster.centroid is None

    def test_cluster_messages_with_persist(self, mock_config):
        """测试向量持久化"""
        mock_embedding = MockEmbeddingProvider(dimension=128)
        mock_clustering = MockClusteringStrategy()
        mock_vector_store = MockVectorStore()

        pipeline = EmbeddingClusterPipeline(
            config=mock_config,
            embedding_provider=mock_embedding,
            clustering_strategy=mock_clustering,
            vector_store=mock_vector_store,
        )

        messages = [
            {"msg_id": "msg_001", "content": "Hello", "chatroom_sender": "user1"},
        ]

        pipeline.cluster_messages("chatroom_001", messages, persist=True)

        # 验证 upsert 被调用
        assert len(mock_vector_store.upsert_calls) == 1
        chatroom_id, stored_messages, embeddings = mock_vector_store.upsert_calls[0]
        assert chatroom_id == "chatroom_001"
        assert len(stored_messages) == 1
        assert len(embeddings) == 1

    def test_cluster_messages_without_persist(self, mock_config):
        """测试不持久化向量"""
        mock_embedding = MockEmbeddingProvider(dimension=128)
        mock_clustering = MockClusteringStrategy()
        mock_vector_store = MockVectorStore()

        pipeline = EmbeddingClusterPipeline(
            config=mock_config,
            embedding_provider=mock_embedding,
            clustering_strategy=mock_clustering,
            vector_store=mock_vector_store,
        )

        messages = [
            {"msg_id": "msg_001", "content": "Hello", "chatroom_sender": "user1"},
        ]

        pipeline.cluster_messages("chatroom_001", messages, persist=False)

        # 验证 upsert 未被调用
        assert len(mock_vector_store.upsert_calls) == 0


class TestClusterResult:
    """ClusterResult 数据类测试"""

    def test_cluster_result_creation(self):
        """测试 ClusterResult 创建"""
        result = ClusterResult(
            cluster_id=0,
            message_ids=["msg_001", "msg_002"],
            messages=[{"msg_id": "msg_001"}, {"msg_id": "msg_002"}],
            centroid=[0.1, 0.2, 0.3],
        )

        assert result.cluster_id == 0
        assert result.message_ids == ["msg_001", "msg_002"]
        assert len(result.messages) == 2
        assert result.centroid == [0.1, 0.2, 0.3]

    def test_cluster_result_defaults(self):
        """测试 ClusterResult 默认值"""
        result = ClusterResult(
            cluster_id=-1,
            message_ids=["msg_001"],
        )

        assert result.cluster_id == -1
        assert result.messages == []
        assert result.centroid is None
