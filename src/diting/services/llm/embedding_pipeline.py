"""Embedding 聚类流水线

协调 Embedding 和聚类流程，将消息转换为向量并进行聚类。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

from diting.services.llm.clustering import Cluster, HDBSCANClusteringStrategy
from diting.services.llm.embedding import OpenAIEmbeddingProvider

if TYPE_CHECKING:
    from diting.services.llm.clustering import ClusteringStrategy
    from diting.services.llm.config import LLMConfig
    from diting.services.llm.embedding import EmbeddingProvider
    from diting.services.llm.vector_store import VectorStore

logger = structlog.get_logger()


@dataclass
class ClusterResult:
    """聚类结果

    Attributes:
        cluster_id: 聚类 ID，-1 表示噪声点
        message_ids: 属于该聚类的消息 ID 列表
        messages: 属于该聚类的消息列表
        centroid: 聚类中心向量（可选）
    """

    cluster_id: int
    message_ids: list[str]
    messages: list[dict[str, Any]] = field(default_factory=list)
    centroid: list[float] | None = None


@dataclass
class EmbeddingBatch:
    """Embedding 批处理结果"""

    message_ids: list[str]
    messages: list[dict[str, Any]]
    embeddings: list[list[float]]
    texts: list[str] = field(default_factory=list)


class EmbeddingClusterPipeline:
    """Embedding 聚类流水线

    协调 Embedding 和聚类流程：
    1. 提取消息文本
    2. 调用 EmbeddingProvider.embed_documents()
    3. 调用 ClusteringStrategy.cluster()
    4. 可选: VectorStore.upsert() 持久化
    5. 返回 ClusterResult 列表
    """

    def __init__(
        self,
        config: LLMConfig,
        embedding_provider: EmbeddingProvider | None = None,
        clustering_strategy: ClusteringStrategy | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        """初始化 Embedding 聚类流水线

        Args:
            config: LLM 配置
            embedding_provider: Embedding 提供者，如果为 None 则根据配置创建
            clustering_strategy: 聚类策略，如果为 None 则根据配置创建
            vector_store: 向量存储，如果为 None 则不持久化
        """
        self.config = config
        self._embedding_provider = embedding_provider or self._create_embedding_provider()
        self._clustering_strategy = clustering_strategy or self._create_clustering_strategy()
        self._vector_store = vector_store

    def _create_embedding_provider(self) -> EmbeddingProvider:
        """根据配置创建 Embedding 提供者"""
        embedding_config = self.config.embedding
        if not embedding_config.api_key:
            raise ValueError("Embedding API key is required")

        return OpenAIEmbeddingProvider(
            api_key=embedding_config.api_key,
            base_url=embedding_config.base_url,
            model=embedding_config.model,
            dimension=embedding_config.dimension,
            batch_size=embedding_config.batch_size,
            timeout=embedding_config.timeout,
        )

    def _create_clustering_strategy(self) -> ClusteringStrategy:
        """根据配置创建聚类策略"""
        clustering_config = self.config.clustering
        return HDBSCANClusteringStrategy(
            min_cluster_size=clustering_config.min_cluster_size,
            min_samples=clustering_config.min_samples,
            metric=clustering_config.metric,
        )

    def cluster_messages(
        self,
        chatroom_id: str,
        messages: list[dict[str, Any]],
        persist: bool = False,
    ) -> list[ClusterResult]:
        """对消息进行聚类

        Args:
            chatroom_id: 聊天室 ID
            messages: 消息列表，每个消息至少包含 msg_id 和 content
            persist: 是否持久化向量到 VectorStore

        Returns:
            聚类结果列表
        """
        batch = self.prepare_embeddings(chatroom_id, messages)
        if not batch.message_ids:
            return []

        if persist:
            self.persist_embeddings(chatroom_id, batch)

        results = self.cluster_embeddings(batch)

        logger.info(
            "embedding_pipeline_completed",
            chatroom_id=chatroom_id,
            cluster_count=len(results),
            noise_count=sum(1 for r in results if r.cluster_id == -1),
        )

        return results

    def prepare_embeddings(
        self, chatroom_id: str, messages: list[dict[str, Any]]
    ) -> EmbeddingBatch:
        """生成 Embedding 批处理结果"""
        if not messages:
            return EmbeddingBatch([], [], [])

        texts = self._extract_texts(messages)
        message_ids = [str(msg.get("msg_id", "")) for msg in messages]

        valid_indices = [i for i, text in enumerate(texts) if text.strip()]
        if not valid_indices:
            logger.warning("embedding_pipeline_no_valid_texts", chatroom_id=chatroom_id)
            return EmbeddingBatch([], [], [])

        valid_texts = [texts[i] for i in valid_indices]
        valid_message_ids = [message_ids[i] for i in valid_indices]
        valid_messages = [messages[i] for i in valid_indices]

        logger.info(
            "embedding_pipeline_started",
            chatroom_id=chatroom_id,
            total_messages=len(messages),
            valid_messages=len(valid_texts),
        )

        try:
            embeddings = self._embedding_provider.embed_documents(valid_texts)
        except Exception as exc:
            logger.error(
                "embedding_pipeline_embed_failed",
                chatroom_id=chatroom_id,
                error=str(exc),
            )
            raise

        return EmbeddingBatch(
            message_ids=valid_message_ids,
            messages=valid_messages,
            embeddings=embeddings,
            texts=valid_texts,
        )

    def persist_embeddings(self, chatroom_id: str, batch: EmbeddingBatch) -> None:
        """持久化向量到 VectorStore"""
        if not self._vector_store:
            return
        try:
            self._vector_store.upsert(chatroom_id, batch.messages, batch.embeddings)
            logger.info(
                "embedding_pipeline_vectors_persisted",
                chatroom_id=chatroom_id,
                count=len(batch.embeddings),
            )
        except Exception as exc:
            logger.warning(
                "embedding_pipeline_persist_failed",
                chatroom_id=chatroom_id,
                error=str(exc),
            )

    def cluster_embeddings(self, batch: EmbeddingBatch) -> list[ClusterResult]:
        """对 Embedding 批处理结果进行聚类"""
        if not batch.message_ids:
            return []

        clusters = self._clustering_strategy.cluster(batch.embeddings, batch.message_ids)
        msg_id_to_message = {str(msg.get("msg_id", "")): msg for msg in batch.messages}
        return self._build_cluster_results(clusters, msg_id_to_message)

    def _extract_texts(self, messages: list[dict[str, Any]]) -> list[str]:
        """从消息中提取文本

        格式: "sender: content"

        Args:
            messages: 消息列表

        Returns:
            文本列表
        """
        texts = []
        for msg in messages:
            sender = msg.get("chatroom_sender") or msg.get("from_username") or "unknown"
            content = str(msg.get("content") or "").strip()
            texts.append(f"{sender}: {content}")
        return texts

    def _build_cluster_results(
        self,
        clusters: list[Cluster],
        msg_id_to_message: dict[str, dict[str, Any]],
    ) -> list[ClusterResult]:
        """构建聚类结果

        Args:
            clusters: 聚类列表
            msg_id_to_message: 消息 ID 到消息的映射

        Returns:
            ClusterResult 列表
        """
        results = []
        for cluster in clusters:
            cluster_messages = [
                msg_id_to_message[msg_id]
                for msg_id in cluster.message_ids
                if msg_id in msg_id_to_message
            ]
            results.append(
                ClusterResult(
                    cluster_id=cluster.cluster_id,
                    message_ids=cluster.message_ids,
                    messages=cluster_messages,
                    centroid=cluster.centroid,
                )
            )
        return results
