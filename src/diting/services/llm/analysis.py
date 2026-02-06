"""群聊消息分析服务

主分析器模块，协调各子模块完成消息分析任务。
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from zoneinfo import ZoneInfo

import pandas as pd
import structlog
from langchain_core.prompts import ChatPromptTemplate

from diting.config import get_llm_config_path, get_messages_parquet_path
from diting.models.llm_analysis import ChatroomAnalysisResult, TopicClassification
from diting.services.llm.config import LLMConfig
from diting.services.llm.debug_writer import DebugWriter
from diting.services.llm.llm_client import LLMClient
from diting.services.llm.message_batcher import DEFAULT_MAX_INPUT_TOKENS, MessageBatcher
from diting.services.llm.message_enricher import enrich_messages_batch
from diting.services.llm.message_formatter import (
    IMAGE_CONTENT_PATTERN,
    MessageFormatter,
    assign_sequence_ids,
    ensure_message_ids,
    load_image_ocr_cache,
    load_image_url_cache,
)
from diting.services.llm.prompts import get_prompts
from diting.services.llm.time_utils import build_date_range
from diting.services.llm.topic_merger import TopicMerger
from diting.services.llm.topic_summarizer import TopicSummarizer
from diting.services.storage.query import query_messages

if TYPE_CHECKING:
    from datetime import tzinfo

    from diting.models.observability import ObservabilityData
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
        enable_observability: bool = False,
    ) -> None:
        """初始化分析器

        Args:
            config: LLM 配置
            debug_dir: 调试输出目录
            db_manager: DuckDB 管理器
            enable_observability: 是否启用 observability 数据收集
        """
        self.config = config
        self._db_manager = db_manager
        self._seq_to_msg_id: dict[int, str] = {}
        self._enable_observability = enable_observability

        # 解析时区配置
        tz_name = config.analysis.timezone
        self._tz: tzinfo | None = ZoneInfo(tz_name) if tz_name and tz_name != "UTC" else None

        # 初始化子模块
        self._debug_writer = DebugWriter(Path(debug_dir) if debug_dir else None)
        self._formatter = MessageFormatter(config, self._tz)
        self._batcher = MessageBatcher(
            max_messages_per_batch=config.analysis.max_messages_per_batch,
            max_tokens=config.analysis.max_input_tokens or DEFAULT_MAX_INPUT_TOKENS,
            formatter=self._formatter,
        )
        self._llm_client = LLMClient(config, seq_to_msg_id=self._seq_to_msg_id)
        self._topic_merger = TopicMerger(config)
        self._topic_summarizer = TopicSummarizer(
            llm_client=self._llm_client,
            formatter=self._formatter,
            batcher=self._batcher,
            debug_writer=self._debug_writer,
        )

        # Observability 收集器
        self._obs_collector = None
        if enable_observability:
            from diting.services.llm.observability_collector import ObservabilityCollector

            self._obs_collector = ObservabilityCollector(
                self._formatter,
                self._tz,
                summary_max_tokens=config.analysis.summary_max_tokens,
            )

        # 初始化提示词
        system_prompt, user_prompt = get_prompts(config.analysis.prompt_version)
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", user_prompt)]
        )

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

        # 设置 observability 收集器的 OCR 缓存
        if self._obs_collector:
            self._obs_collector.set_image_ocr_cache(image_ocr_cache)
            # 加载图片 URL 缓存用于预览
            image_url_cache = load_image_url_cache(sorted_messages, self._db_manager)
            self._obs_collector.set_image_url_cache(image_url_cache)

        message_lookup = {
            str(message.get("msg_id")): message
            for message in sorted_messages
            if message.get("msg_id")
        }
        overall_date_range = build_date_range(sorted_messages, self._tz)
        overall_total = len(sorted_messages)

        # 分批消息
        batches = self._batcher.split_messages(sorted_messages)

        if not batches:
            return ChatroomAnalysisResult(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=overall_date_range,
                total_messages=overall_total,
            )

        # 设置调试目录
        self._debug_writer.set_chatroom_dir(chatroom_id)

        # 分析各批次
        topics: list[TopicClassification] = []
        for batch_index, batch in enumerate(batches, start=1):
            # 收集 observability 数据
            if self._obs_collector:
                self._obs_collector.collect_batch(batch_index, batch)

            batch_result = self._analyze_batch(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=build_date_range(batch, self._tz),
                total_messages=len(batch),
                messages=batch,
                batch_index=batch_index,
            )
            topics.extend(batch_result.topics)

        # 合并话题
        logger.info(
            "topic_merge_started",
            chatroom_id=chatroom_id,
            topics_before_merge=len(topics),
        )
        topics, merge_logs = self._topic_merger.merge_topics(topics)
        self._debug_writer.write_merge_report(merge_logs)
        logger.info(
            "topic_merge_completed",
            chatroom_id=chatroom_id,
            topics_after_merge=len(topics),
            merges_performed=len(merge_logs),
        )

        # 过滤低热度话题
        topics_before_filter = len(topics)
        topics = [
            topic for topic in topics if _topic_popularity(topic) > DEFAULT_POPULARITY_THRESHOLD
        ]
        logger.info(
            "topic_filter_completed",
            chatroom_id=chatroom_id,
            topics_before_filter=topics_before_filter,
            topics_after_filter=len(topics),
            filtered_count=topics_before_filter - len(topics),
            popularity_threshold=DEFAULT_POPULARITY_THRESHOLD,
        )
        if not topics:
            return ChatroomAnalysisResult(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=overall_date_range,
                total_messages=overall_total,
                topics=[],
            )

        # 生成摘要
        logger.info(
            "topic_summarize_started",
            chatroom_id=chatroom_id,
            topics_to_summarize=len(topics),
        )
        summary_start_time = time.perf_counter()
        topics = self._topic_summarizer.summarize_topics(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=overall_date_range,
            topics=topics,
            message_lookup=message_lookup,
        )
        summary_elapsed_ms = (time.perf_counter() - summary_start_time) * 1000
        logger.info(
            "topic_summarize_completed",
            chatroom_id=chatroom_id,
            topics_summarized=len(topics),
            elapsed_ms=round(summary_elapsed_ms, 1),
        )

        # 记录批次数量用于 observability
        self._last_batch_count = len(batches)

        return ChatroomAnalysisResult(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=overall_date_range,
            total_messages=overall_total,
            topics=topics,
        )

    def get_observability_data(self, result: ChatroomAnalysisResult) -> ObservabilityData | None:
        """获取 observability 数据

        Args:
            result: 群聊分析结果

        Returns:
            ObservabilityData 对象，如果未启用则返回 None
        """
        if not self._obs_collector:
            return None
        batch_count = getattr(self, "_last_batch_count", 0)
        return self._obs_collector.build_full_data(result, batch_count)

    def reset_observability(self) -> None:
        """重置 observability 收集器状态"""
        if self._obs_collector:
            self._obs_collector.reset()

    def _analyze_batch(
        self,
        chatroom_id: str,
        chatroom_name: str,
        date_range: str,
        total_messages: int,
        messages: list[dict[str, Any]],
        batch_index: int,
    ) -> ChatroomAnalysisResult:
        """分析单个批次

        Args:
            chatroom_id: 群聊 ID
            chatroom_name: 群聊名称
            date_range: 日期范围
            total_messages: 消息总数
            messages: 消息列表
            batch_index: 批次索引

        Returns:
            分析结果
        """
        # 格式化消息并过滤空行
        formatted_lines = [self._formatter.format_message_line(message) for message in messages]
        filtered_count = sum(1 for line in formatted_lines if not line)
        formatted_messages = "\n".join(line for line in formatted_lines if line).strip()

        if filtered_count > 0:
            logger.debug(
                "batch_messages_filtered",
                chatroom_id=chatroom_id,
                batch_index=batch_index,
                total_messages=total_messages,
                filtered_count=filtered_count,
            )

        if self._debug_writer.chatroom_dir:
            self._debug_writer.write(
                self._debug_writer.chatroom_dir / f"batch_{batch_index:02d}_input.txt",
                DebugWriter.render_batch_debug_header(
                    chatroom_id, chatroom_name, date_range, total_messages
                )
                + "\n"
                + formatted_messages,
            )

        prompt_messages = self.prompt.format_messages(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=date_range,
            total_messages=total_messages,
            messages=formatted_messages or "（无有效内容）",
        )

        prompt_name = (
            "SYSTEM_PROMPT_V2+USER_PROMPT_V2"
            if self.config.analysis.prompt_version == "v2"
            else "SYSTEM_PROMPT_V1+USER_PROMPT_V1"
        )
        start_time = time.perf_counter()
        response_text = self._llm_client.invoke_with_retry(prompt_messages, prompt_name=prompt_name)
        if self._debug_writer.chatroom_dir:
            self._debug_writer.write(
                self._debug_writer.chatroom_dir / f"batch_{batch_index:02d}_output.txt",
                response_text,
            )
        result = self._llm_client.parse_response(response_text)
        if self._debug_writer.chatroom_dir:
            self._debug_writer.write(
                self._debug_writer.chatroom_dir / f"batch_{batch_index:02d}_topics.txt",
                DebugWriter.format_topics_for_debug(result.topics),
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "batch_analysis_completed",
            chatroom_id=chatroom_id,
            batch_index=batch_index,
            total_messages=total_messages,
            topics_found=len(result.topics),
            elapsed_ms=round(elapsed_ms, 1),
        )

        updated = result.model_copy(
            update={
                "chatroom_id": chatroom_id,
                "chatroom_name": chatroom_name,
                "date_range": date_range,
                "total_messages": total_messages,
            }
        )
        return cast(ChatroomAnalysisResult, updated)

    def verify_codex_cli_availability(self) -> None:
        """使用简短提示词验证 Codex CLI 可用性"""
        if self.config.api.provider.lower() != "codex-cli":
            return
        logger.info("codex_cli_health_check_start")
        probe_messages = [
            {
                "content": "Reply with OK.",
            }
        ]
        response = self._llm_client.invoke_with_retry(
            probe_messages,
            prompt_name="CODEX_CLI_HEALTH_CHECK",
        )
        logger.info(
            "codex_cli_health_check_completed",
            response_preview=response[:50],
        )


def analyze_chatrooms_from_parquet(
    start_date: str,
    end_date: str,
    parquet_root: str | Path | None = None,
    config_path: str | Path | None = None,
    chatroom_ids: list[str] | None = None,
    debug_dir: str | Path | None = None,
    db_manager: DuckDBManager | None = None,
    enable_observability: bool = False,
) -> tuple[list[ChatroomAnalysisResult], list[ObservabilityData]]:
    """从 Parquet 中读取群聊消息并分析

    Args:
        start_date: 开始日期
        end_date: 结束日期
        parquet_root: Parquet 根目录
        config_path: LLM 配置文件路径
        chatroom_ids: 限定的群聊 ID 列表
        debug_dir: 调试输出目录
        db_manager: DuckDB 管理器 (用于图片 OCR 内容替换)
        enable_observability: 是否启用 observability 数据收集

    Returns:
        元组 (群聊分析结果列表, observability 数据列表)
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
        enable_observability=enable_observability,
    )
    analyzer.verify_codex_cli_availability()

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
        return [], []

    df = df[df["is_chatroom_msg"] == 1]
    if chatroom_ids:
        chatroom_set = {str(chatroom_id).strip() for chatroom_id in chatroom_ids}
        df = df[df["chatroom"].astype(str).isin(chatroom_set)]
        if df.empty:
            logger.info("no_chatroom_messages_found", chatroom_ids=list(chatroom_set))
            return [], []

    results: list[ChatroomAnalysisResult] = []
    observability_data: list[ObservabilityData] = []

    for chatroom_id, group in df.groupby("chatroom"):
        if not chatroom_id or (isinstance(chatroom_id, float) and pd.isna(chatroom_id)):
            continue
        records: list[dict[str, Any]] = cast(
            list[dict[str, Any]],
            group.sort_values("create_time").to_dict(orient="records"),
        )
        if config.analysis.enable_xml_parsing:
            records = enrich_messages_batch(records)

        # 重置 observability 收集器
        analyzer.reset_observability()

        result = analyzer.analyze_chatroom(str(chatroom_id), records)
        results.append(result)

        # 收集 observability 数据
        if enable_observability:
            obs_data = analyzer.get_observability_data(result)
            if obs_data:
                observability_data.append(obs_data)

    return results, observability_data
