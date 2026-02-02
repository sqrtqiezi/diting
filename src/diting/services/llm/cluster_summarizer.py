"""聚类摘要生成器

为 Embedding 聚类生成标题、分类、关键词和摘要。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from langchain_core.prompts import ChatPromptTemplate

from diting.models.llm_analysis import TopicClassification
from diting.services.llm.response_parser import parse_topics_from_text
from diting.services.llm.time_utils import build_time_range

if TYPE_CHECKING:
    from diting.services.llm.debug_writer import DebugWriter
    from diting.services.llm.embedding_pipeline import ClusterResult
    from diting.services.llm.llm_client import LLMClient
    from diting.services.llm.message_formatter import MessageFormatter

logger = structlog.get_logger()

# 聚类摘要提示词（使用 <<<TOPIC>>> 分隔符格式，与 response_parser 兼容）
CLUSTER_SUMMARY_SYSTEM_PROMPT = """\
你是一个群聊消息分析助手。你的任务是分析一组语义相似的消息，提取话题信息。

请根据消息内容，生成以下信息：
1. title: 简洁的话题标题（10-20字）
2. category: 话题分类（只能从以下四类中选择其一：时事 / 投资理财 / 工作生活 / 迪子）
3. keywords: 3-5个关键词，用逗号分隔
4. summary: 话题摘要（100-200字）
5. notes: 补充说明（可选）

分类说明（基于本群历史内容）：
- 时事：政治/国际关系/公共安全/政策发布/社会热点/疫情与公共卫生/法规与官方公告等。
  例：美国ICE执法争议、伊朗局势、尼帕病毒疫情、联合国搬迁讨论、政策讲话与外交动态。
- 投资理财：股票/基金/期货/贵金属/加密货币/宏观与市场行情/仓位与交易策略等。
  例：黄金白银行情、比亚迪股价、ETF机制、比特币走势、军工与大宗商品波动。
- 工作生活：工作场景/职场关系/家庭与情感/日常生活/消费体验/科技产品/娱乐内容/美食出行等。
  例：同事打听隐私、领导开会、记账理财方式、产品体验与直播讨论、聚会与美食分享。
- 迪子：只要话题核心与“比亚迪/迪子/朝阳老师/91迪先生/迪链”等强相关，就单独归类为“迪子”。
  例：比亚迪股价、加仓/减仓讨论、朝阳老师观点、迪子调侃与盘口分析。

分类优先级：
- 若与“比亚迪/迪子/朝阳老师/91迪先生”直接相关，优先归为“迪子”，即使同时涉及投资讨论。
- 若同时涉及“时事/政策”与“市场影响”，以讨论重心为准：
  - 重心在投资决策/行情/交易 -> 投资理财
  - 重心在事件本身/社会影响 -> 时事
- 娱乐、科技产品体验、社交互动等均归入“工作生活”。

输出格式（严格遵循）：
<<<TOPIC>>>
title: 话题标题
category: 分类
keywords: 关键词1, 关键词2, 关键词3
summary: 话题摘要内容
notes: 补充说明"""

CLUSTER_SUMMARY_USER_PROMPT = """群聊: {chatroom_name}
日期范围: {date_range}
消息数量: {message_count}

以下是该聚类中的消息：
{messages}

请分析这些消息，按照指定格式输出话题信息。"""

# 噪声点处理提示词
NOISE_SUMMARY_SYSTEM_PROMPT = """\
你是一个群聊消息分析助手。你的任务是分析一组零散的消息，尝试提取共同话题。

这些消息可能没有明显的共同主题，请尽量找出它们的共同点。\
如果确实没有共同主题，可以将其归类为"其他讨论"。

请根据消息内容，生成以下信息：
1. title: 简洁的话题标题（10-20字）
2. category: 话题分类（只能从以下四类中选择其一：时事 / 投资理财 / 工作生活 / 迪子）
3. keywords: 3-5个关键词，用逗号分隔
4. summary: 话题摘要（100-200字）
5. notes: 补充说明（可选）

分类说明：
- 时事：政治/国际关系/公共安全/政策发布/社会热点/疫情与公共卫生/法规与官方公告等。
- 投资理财：股票/基金/期货/贵金属/加密货币/宏观与市场行情/仓位与交易策略等。
- 工作生活：工作场景/职场关系/家庭与情感/日常生活/消费体验/科技产品/娱乐内容/美食出行等。
- 迪子：与“比亚迪/迪子/朝阳老师/91迪先生/迪链”等强相关话题。

分类优先级：
- 若与“比亚迪/迪子/朝阳老师/91迪先生”直接相关，优先归为“迪子”，即使同时涉及投资讨论。
- 若同时涉及“时事/政策”与“市场影响”，以讨论重心为准：
  - 重心在投资决策/行情/交易 -> 投资理财
  - 重心在事件本身/社会影响 -> 时事
- 娱乐、科技产品体验、社交互动等均归入“工作生活”。

输出格式（严格遵循）：
<<<TOPIC>>>
title: 话题标题
category: 分类
keywords: 关键词1, 关键词2, 关键词3
summary: 话题摘要内容
notes: 补充说明"""

# 噪声点低置信度阈值
NOISE_MIN_MESSAGES = 3


class ClusterSummarizer:
    """聚类摘要生成器

    为 Embedding 聚类生成标题、分类、关键词和摘要。
    """

    def __init__(
        self,
        llm_client: LLMClient,
        formatter: MessageFormatter,
        debug_writer: DebugWriter | None = None,
    ) -> None:
        """初始化聚类摘要生成器

        Args:
            llm_client: LLM 客户端
            formatter: 消息格式化器
            debug_writer: 调试输出器
        """
        self.llm_client = llm_client
        self.formatter = formatter
        self.debug_writer = debug_writer

        # 初始化提示词
        self.cluster_prompt = ChatPromptTemplate.from_messages(
            [("system", CLUSTER_SUMMARY_SYSTEM_PROMPT), ("human", CLUSTER_SUMMARY_USER_PROMPT)]
        )
        self.noise_prompt = ChatPromptTemplate.from_messages(
            [("system", NOISE_SUMMARY_SYSTEM_PROMPT), ("human", CLUSTER_SUMMARY_USER_PROMPT)]
        )

    def summarize_clusters(
        self,
        chatroom_id: str,
        chatroom_name: str,
        date_range: str,
        clusters: list[ClusterResult],
    ) -> list[TopicClassification]:
        """为聚类列表生成摘要

        Args:
            chatroom_id: 群聊 ID
            chatroom_name: 群聊名称
            date_range: 日期范围
            clusters: 聚类结果列表

        Returns:
            话题分类列表
        """
        topics: list[TopicClassification] = []

        # 分离正常聚类和噪声点
        normal_clusters = [c for c in clusters if c.cluster_id >= 0]
        noise_clusters = [c for c in clusters if c.cluster_id == -1]

        # 处理正常聚类
        for cluster in normal_clusters:
            topic = self._summarize_single_cluster(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=date_range,
                cluster=cluster,
                is_noise=False,
            )
            if topic:
                topics.append(topic)

        # 处理噪声点
        noise_topic = self._handle_noise_clusters(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=date_range,
            noise_clusters=noise_clusters,
        )
        if noise_topic:
            topics.append(noise_topic)

        logger.info(
            "cluster_summarizer_completed",
            chatroom_id=chatroom_id,
            total_clusters=len(clusters),
            topics_generated=len(topics),
        )

        return topics

    def _summarize_single_cluster(
        self,
        chatroom_id: str,
        chatroom_name: str,
        date_range: str,
        cluster: ClusterResult,
        is_noise: bool = False,
        low_count: bool = False,
    ) -> TopicClassification | None:
        """为单个聚类生成摘要

        Args:
            chatroom_id: 群聊 ID
            chatroom_name: 群聊名称
            date_range: 日期范围
            cluster: 聚类结果
            is_noise: 是否为噪声点聚类

        Returns:
            话题分类，如果生成失败则返回 None
        """
        messages = cluster.messages
        if not messages:
            return None

        # 格式化消息
        formatted_messages = "\n".join(
            self.formatter.format_message_line_for_summary(msg) for msg in messages
        ).strip()

        # 选择提示词
        prompt = self.noise_prompt if is_noise else self.cluster_prompt

        prompt_messages = prompt.format_messages(
            chatroom_name=chatroom_name,
            date_range=date_range,
            message_count=len(messages),
            messages=formatted_messages or "（无有效内容）",
        )

        try:
            response_text = self.llm_client.invoke_with_retry(prompt_messages)
            topic_dicts, warnings = parse_topics_from_text(response_text)

            for warning in warnings:
                logger.warning(
                    "cluster_summarizer_parse_warning",
                    cluster_id=cluster.cluster_id,
                    warning=warning,
                )

            if topic_dicts:
                first = topic_dicts[0]
                return self._build_topic_classification(
                    cluster=cluster,
                    topic_dict=first,
                    is_noise=is_noise,
                    low_count=low_count,
                )
        except Exception as exc:
            logger.error(
                "cluster_summarizer_failed",
                chatroom_id=chatroom_id,
                cluster_id=cluster.cluster_id,
                error=str(exc),
            )

        # 回退：使用默认值
        return self._build_fallback_topic(cluster, is_noise, low_count=low_count)

    def _handle_noise_clusters(
        self,
        chatroom_id: str,
        chatroom_name: str,
        date_range: str,
        noise_clusters: list[ClusterResult],
    ) -> TopicClassification | None:
        """处理噪声点聚类

        Args:
            chatroom_id: 群聊 ID
            chatroom_name: 群聊名称
            date_range: 日期范围
            noise_clusters: 噪声点聚类列表

        Returns:
            话题分类，如果消息数不足则返回 None
        """
        if not noise_clusters:
            return None

        # 合并所有噪声点消息
        all_messages: list[dict[str, Any]] = []
        all_message_ids: list[str] = []
        for cluster in noise_clusters:
            all_messages.extend(cluster.messages)
            all_message_ids.extend(cluster.message_ids)

        low_count = len(all_messages) < NOISE_MIN_MESSAGES
        if self.debug_writer:
            self._write_noise_debug(chatroom_id, noise_clusters, low_count)

        # 创建合并的聚类结果
        from diting.services.llm.embedding_pipeline import ClusterResult

        merged_cluster = ClusterResult(
            cluster_id=-1,
            message_ids=all_message_ids,
            messages=all_messages,
            centroid=None,
        )

        return self._summarize_single_cluster(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=date_range,
            cluster=merged_cluster,
            is_noise=True,
            low_count=low_count,
        )

    def _build_topic_classification(
        self,
        cluster: ClusterResult,
        topic_dict: dict[str, Any],
        is_noise: bool,
        low_count: bool = False,
    ) -> TopicClassification:
        """构建话题分类对象

        Args:
            cluster: 聚类结果
            topic_dict: LLM 返回的话题字典
            is_noise: 是否为噪声点聚类

        Returns:
            话题分类对象
        """
        messages = cluster.messages
        participants = self._extract_participants(messages)
        time_range = build_time_range(messages, self.formatter.tz)

        notes = topic_dict.get("notes") or ""
        confidence = 0.5 if is_noise else 1.0
        if is_noise and low_count:
            confidence = min(confidence, 0.3)
            notes = self._append_note(notes, "噪声消息数较少，置信度降低")

        return TopicClassification(
            title=topic_dict.get("title") or ("其他讨论" if is_noise else "未命名话题"),
            category=topic_dict.get("category") or "其他",
            summary=topic_dict.get("summary") or "",
            time_range=time_range,
            participants=participants,
            message_count=len(messages),
            keywords=topic_dict.get("keywords") or [],
            message_ids=cluster.message_ids,
            confidence=confidence,
            notes=notes,
        )

    def _build_fallback_topic(
        self,
        cluster: ClusterResult,
        is_noise: bool,
        low_count: bool = False,
    ) -> TopicClassification:
        """构建回退话题分类对象

        当 LLM 调用失败时使用。

        Args:
            cluster: 聚类结果
            is_noise: 是否为噪声点聚类

        Returns:
            话题分类对象
        """
        messages = cluster.messages
        participants = self._extract_participants(messages)
        time_range = build_time_range(messages, self.formatter.tz)

        notes = "LLM 摘要生成失败，使用默认值"
        confidence = 0.3 if is_noise else 0.5
        if is_noise and low_count:
            confidence = min(confidence, 0.3)
            notes = self._append_note(notes, "噪声消息数较少，置信度降低")

        return TopicClassification(
            title="其他讨论" if is_noise else f"话题 {cluster.cluster_id + 1}",
            category="其他",
            summary="",
            time_range=time_range,
            participants=participants,
            message_count=len(messages),
            keywords=[],
            message_ids=cluster.message_ids,
            confidence=confidence,
            notes=notes,
        )

    @staticmethod
    def _extract_participants(messages: list[dict[str, Any]]) -> list[str]:
        """提取参与者列表

        Args:
            messages: 消息列表

        Returns:
            参与者列表
        """
        participants = []
        for message in messages:
            sender = message.get("chatroom_sender") or message.get("from_username")
            if sender:
                participants.append(str(sender))
        return sorted(set(participants))

    def _write_noise_debug(
        self,
        chatroom_id: str,
        noise_clusters: list[ClusterResult],
        low_count: bool,
    ) -> None:
        if not self.debug_writer or not self.debug_writer.chatroom_dir:
            return

        all_messages: list[dict[str, Any]] = []
        for cluster in noise_clusters:
            all_messages.extend(cluster.messages)

        sorted_messages = sorted(all_messages, key=lambda msg: msg.get("create_time") or 0)
        lines = [
            f"chatroom_id: {chatroom_id}",
            f"noise_clusters: {len(noise_clusters)}",
            f"noise_messages: {len(sorted_messages)}",
            f"below_threshold: {low_count} (threshold={NOISE_MIN_MESSAGES})",
            "",
            "messages:",
        ]
        for message in sorted_messages:
            lines.append(self.formatter.format_message_line_for_summary(message))

        self.debug_writer.write_to_chatroom("noise_messages.txt", "\n".join(lines).strip())

    @staticmethod
    def _append_note(notes: str, extra: str) -> str:
        if not notes:
            return extra
        return f"{notes}；{extra}"
