"""群聊消息分析服务

主分析器模块，协调各子模块完成消息分析任务。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from zoneinfo import ZoneInfo

import pandas as pd
import structlog

from diting.config import get_llm_config_path, get_messages_parquet_path
from diting.models.llm_analysis import ChatroomAnalysisResult, TopicClassification
from diting.services.llm.cluster_summarizer import ClusterSummarizer
from diting.services.llm.config import LLMConfig
from diting.services.llm.debug_writer import DebugWriter
from diting.services.llm.embedding_pipeline import ClusterResult, EmbeddingClusterPipeline
from diting.services.llm.llm_client import LLMClient
from diting.services.llm.message_enricher import enrich_messages_batch
from diting.services.llm.message_formatter import (
    IMAGE_CONTENT_PATTERN,
    MessageFormatter,
    assign_sequence_ids,
    ensure_message_ids,
    load_image_ocr_cache,
)
from diting.services.llm.time_utils import build_date_range
from diting.services.llm.topic_merger import TopicMerger
from diting.services.llm.topic_threader import TopicThreader
from diting.services.storage.query import query_messages

if TYPE_CHECKING:
    from datetime import tzinfo

    from diting.services.storage.duckdb_manager import DuckDBManager

logger = structlog.get_logger()

DEFAULT_POPULARITY_THRESHOLD = 5.0

# 重新导出 IMAGE_CONTENT_PATTERN 以保持向后兼容
__all__ = [
    "IMAGE_CONTENT_PATTERN",
    "ChatroomMessageAnalyzer",
    "analyze_chatrooms_from_parquet",
]


def _topic_popularity(topic: TopicClassification) -> float:
    """计算话题热度分数

    Args:
        topic: 话题分类对象

    Returns:
        热度分数
    """
    participants = cast(list[str], topic.participants or [])
    u_count = len(set(participants))
    m_count = int(cast(int, topic.message_count or 0))
    if u_count <= 0 or m_count <= 0:
        return 0.0
    ratio = m_count / u_count
    penalty = 1 + max(0.0, ratio - 6)
    score = math.log(1 + u_count) ** 1.2 * math.log(1 + m_count) ** 0.8 * (1 / (penalty**0.4))
    return float(score)


class ChatroomMessageAnalyzer:
    """群聊消息分析器

    协调各子模块完成消息分析任务。
    """

    def __init__(
        self,
        config: LLMConfig,
        debug_dir: Path | None = None,
        db_manager: DuckDBManager | None = None,
    ) -> None:
        """初始化分析器

        Args:
            config: LLM 配置
            debug_dir: 调试输出目录
            db_manager: DuckDB 管理器
        """
        self.config = config
        self._db_manager = db_manager
        self._seq_to_msg_id: dict[int, str] = {}

        # 解析时区配置
        tz_name = config.analysis.timezone
        self._tz: tzinfo | None = ZoneInfo(tz_name) if tz_name and tz_name != "UTC" else None

        # 初始化子模块
        self._debug_writer = DebugWriter(Path(debug_dir) if debug_dir else None)
        self._formatter = MessageFormatter(config, self._tz)
        self._llm_client = LLMClient(config, seq_to_msg_id=self._seq_to_msg_id)
        self._topic_merger = TopicMerger(config)

        # 初始化 Embedding 相关组件（如果启用）
        self._embedding_pipeline: EmbeddingClusterPipeline | None = None
        self._cluster_summarizer: ClusterSummarizer | None = None
        if config.embedding.enabled:
            # 创建向量存储（如果配置了 db_path）
            vector_store = None
            if config.vector_store.db_path:
                from diting.services.llm.vector_store import DuckDBVectorStore

                # 使用 embedding 配置的维度，确保一致性
                vector_store = DuckDBVectorStore(
                    db_path=config.vector_store.db_path,
                    dimension=config.embedding.dimension,
                )
            self._embedding_pipeline = EmbeddingClusterPipeline(
                config=config,
                vector_store=vector_store,
            )
            self._cluster_summarizer = ClusterSummarizer(
                llm_client=self._llm_client,
                formatter=self._formatter,
                debug_writer=self._debug_writer,
            )
        else:
            raise ValueError("Embedding analysis is required. Set embedding.enabled = true.")

    def analyze_chatroom(
        self, chatroom_id: str, messages: list[dict[str, Any]], chatroom_name: str = ""
    ) -> ChatroomAnalysisResult:
        """分析单个群聊消息

        Args:
            chatroom_id: 群聊 ID
            messages: 消息列表
            chatroom_name: 群聊名称

        Returns:
            分析结果
        """
        if not messages:
            return ChatroomAnalysisResult(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range="",
                total_messages=0,
            )

        # 预处理消息
        sorted_messages = ensure_message_ids(
            sorted(messages, key=lambda item: item.get("create_time", 0))
        )
        sorted_messages = assign_sequence_ids(sorted_messages)
        self._seq_to_msg_id = {
            int(message["seq_id"]): message["msg_id"] for message in sorted_messages
        }
        self._llm_client.seq_to_msg_id = self._seq_to_msg_id

        # 加载图片 OCR 缓存
        image_ocr_cache = load_image_ocr_cache(
            sorted_messages,
            self._db_manager,
            self.config.analysis.enable_image_ocr_display,
        )
        self._formatter.image_ocr_cache = image_ocr_cache

        overall_date_range = build_date_range(sorted_messages, self._tz)
        overall_total = len(sorted_messages)

        # 设置调试目录
        self._debug_writer.set_chatroom_dir(chatroom_id)

        # 根据配置选择分析流程
        if not self._embedding_pipeline or not self._cluster_summarizer:
            raise ValueError("Embedding analysis is not initialized.")

        topics = self._analyze_with_embedding(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=overall_date_range,
            messages=sorted_messages,
        )

        if not topics:
            return ChatroomAnalysisResult(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=overall_date_range,
                total_messages=overall_total,
                topics=[],
            )

        # 合并话题
        topics, merge_logs = self._topic_merger.merge_topics(topics)
        self._debug_writer.write_merge_report(merge_logs)

        # 过滤低热度话题
        topics = [
            topic for topic in topics if _topic_popularity(topic) > DEFAULT_POPULARITY_THRESHOLD
        ]
        if not topics:
            return ChatroomAnalysisResult(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=overall_date_range,
                total_messages=overall_total,
                topics=[],
            )

        return ChatroomAnalysisResult(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=overall_date_range,
            total_messages=overall_total,
            topics=topics,
        )

    def _analyze_with_embedding(
        self,
        chatroom_id: str,
        chatroom_name: str,
        date_range: str,
        messages: list[dict[str, Any]],
    ) -> list[TopicClassification]:
        """使用 Embedding 聚类流程分析消息

        Args:
            chatroom_id: 群聊 ID
            chatroom_name: 群聊名称
            date_range: 日期范围
            messages: 消息列表

        Returns:
            话题分类列表
        """
        if not self._embedding_pipeline or not self._cluster_summarizer:
            return []

        logger.info(
            "embedding_analysis_started",
            chatroom_id=chatroom_id,
            total_messages=len(messages),
        )

        # 1. Embedding 聚类
        batch = self._embedding_pipeline.prepare_embeddings(chatroom_id, messages)
        if not batch.message_ids:
            logger.warning("embedding_analysis_no_embeddings", chatroom_id=chatroom_id)
            return []

        if self.config.vector_store.db_path:
            self._embedding_pipeline.persist_embeddings(chatroom_id, batch)

        if self.config.threading.enabled:
            threader = TopicThreader(self.config.threading, tz=self._tz)
            thread_batches = threader.split_batch(batch)
            clusters: list[ClusterResult] = []
            for thread_batch in thread_batches:
                clusters.extend(self._embedding_pipeline.cluster_embeddings(thread_batch))
        else:
            clusters = self._embedding_pipeline.cluster_embeddings(batch)

        if not clusters:
            logger.warning("embedding_analysis_no_clusters", chatroom_id=chatroom_id)
            return []

        # 2. 为聚类生成摘要
        topics = self._cluster_summarizer.summarize_clusters(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=date_range,
            clusters=clusters,
        )

        logger.info(
            "embedding_analysis_completed",
            chatroom_id=chatroom_id,
            cluster_count=len(clusters),
            topic_count=len(topics),
        )

        return topics


def analyze_chatrooms_from_parquet(
    start_date: str,
    end_date: str,
    parquet_root: str | Path | None = None,
    config_path: str | Path | None = None,
    chatroom_ids: list[str] | None = None,
    debug_dir: str | Path | None = None,
    db_manager: DuckDBManager | None = None,
) -> list[ChatroomAnalysisResult]:
    """从 Parquet 中读取群聊消息并分析

    Args:
        start_date: 开始日期
        end_date: 结束日期
        parquet_root: Parquet 根目录
        config_path: LLM 配置文件路径
        chatroom_ids: 限定的群聊 ID 列表
        debug_dir: 调试输出目录
        db_manager: DuckDB 管理器 (用于图片 OCR 内容替换)

    Returns:
        群聊分析结果列表
    """
    if parquet_root is None:
        parquet_root = get_messages_parquet_path()
    if config_path is None:
        config_path = get_llm_config_path()

    config = LLMConfig.load_from_yaml(config_path)
    analyzer = ChatroomMessageAnalyzer(
        config,
        Path(debug_dir) if debug_dir else None,
        db_manager=db_manager,
    )

    df = query_messages(
        start_date=start_date,
        end_date=end_date,
        parquet_root=parquet_root,
        filters={"is_chatroom_msg": 1},
        columns=[
            "chatroom",
            "chatroom_sender",
            "from_username",
            "content",
            "create_time",
            "is_chatroom_msg",
            "msg_id",
            "msg_type",
        ],
    )

    if df.empty:
        logger.info("no_chatroom_messages_found")
        return []

    df = df[df["is_chatroom_msg"] == 1]
    if chatroom_ids:
        chatroom_set = {str(chatroom_id).strip() for chatroom_id in chatroom_ids}
        df = df[df["chatroom"].astype(str).isin(chatroom_set)]
        if df.empty:
            logger.info("no_chatroom_messages_found", chatroom_ids=list(chatroom_set))
            return []
    results: list[ChatroomAnalysisResult] = []
    for chatroom_id, group in df.groupby("chatroom"):
        if not chatroom_id or (isinstance(chatroom_id, float) and pd.isna(chatroom_id)):
            continue
        records: list[dict[str, Any]] = cast(
            list[dict[str, Any]],
            group.sort_values("create_time").to_dict(orient="records"),
        )
        if config.analysis.enable_xml_parsing:
            records = enrich_messages_batch(records)
        results.append(analyzer.analyze_chatroom(str(chatroom_id), records))

    return results
