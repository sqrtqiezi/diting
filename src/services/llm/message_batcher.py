"""消息分批模块

提供消息分批策略，支持按数量和按 Token 数分批。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.services.llm.message_formatter import MessageFormatter

DEFAULT_MAX_INPUT_TOKENS = 120_000


class MessageBatcher:
    """消息分批器

    负责将消息列表按照配置的策略分批。
    """

    def __init__(
        self,
        max_messages_per_batch: int | None = None,
        max_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
        formatter: MessageFormatter | None = None,
    ) -> None:
        """初始化消息分批器

        Args:
            max_messages_per_batch: 每批最大消息数，如果为 None 则使用 Token 分批
            max_tokens: 每批最大 Token 数
            formatter: 消息格式化器，用于估算 Token 数
        """
        self.max_messages_per_batch = max_messages_per_batch
        self.max_tokens = max_tokens
        self.formatter = formatter
        self._token_encoder: Any = None

    def split_messages(self, messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """根据配置分批消息

        Args:
            messages: 消息列表

        Returns:
            分批后的消息列表
        """
        if self.max_messages_per_batch:
            return self.split_by_count(messages)
        return self.split_by_tokens(messages)

    def split_by_count(self, messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """按数量分批消息

        Args:
            messages: 消息列表

        Returns:
            分批后的消息列表
        """
        max_messages = self.max_messages_per_batch
        if not max_messages:
            return [messages]
        return [
            messages[index : index + max_messages]
            for index in range(0, len(messages), max_messages)
        ]

    def split_by_tokens(self, messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """按 Token 数分批消息

        Args:
            messages: 消息列表

        Returns:
            分批后的消息列表
        """
        if not self.formatter:
            return [messages]

        batches: list[list[dict[str, Any]]] = []
        current_batch: list[dict[str, Any]] = []
        current_tokens = 0

        for message in messages:
            line = self.formatter.format_message_line(message)
            line_tokens = self.estimate_tokens(line) + 1
            if current_batch and current_tokens + line_tokens > self.max_tokens:
                batches.append(current_batch)
                current_batch = [message]
                current_tokens = line_tokens
            else:
                current_batch.append(message)
                current_tokens += line_tokens

        if current_batch:
            batches.append(current_batch)

        return batches

    def estimate_tokens(self, text: str) -> int:
        """估算文本的 Token 数

        Args:
            text: 文本内容

        Returns:
            估算的 Token 数
        """
        if self._token_encoder is None:
            try:
                import tiktoken

                self._token_encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self._token_encoder = False
        if self._token_encoder:
            return len(self._token_encoder.encode(text))
        return max(1, len(text) // 4)

    def chunk_messages_for_summary(
        self, messages: list[dict[str, Any]], max_tokens: int | None = None
    ) -> list[list[dict[str, Any]]]:
        """为摘要生成分块消息

        Args:
            messages: 消息列表
            max_tokens: 每块最大 Token 数

        Returns:
            分块后的消息列表
        """
        if not max_tokens or not self.formatter:
            return [messages]

        chunks: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []
        current_tokens = 0
        for message in messages:
            line = self.formatter.format_message_line_for_summary(message)
            line_tokens = self.estimate_tokens(line) + 1
            if current and current_tokens + line_tokens > max_tokens:
                chunks.append(current)
                current = [message]
                current_tokens = line_tokens
            else:
                current.append(message)
                current_tokens += line_tokens
        if current:
            chunks.append(current)
        return chunks

    def select_messages_for_summary(
        self, messages: list[dict[str, Any]], max_messages: int | None = None
    ) -> list[dict[str, Any]]:
        """选择用于摘要的消息

        Args:
            messages: 消息列表
            max_messages: 最大消息数

        Returns:
            选择后的消息列表
        """
        if not messages:
            return messages

        selected = messages
        if max_messages and len(selected) > max_messages:
            step = max(1, len(selected) // max_messages)
            selected = selected[::step]
        return selected
