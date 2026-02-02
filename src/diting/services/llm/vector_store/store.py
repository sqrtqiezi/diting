"""向量存储协议

定义向量存储的统一接口。
"""

from __future__ import annotations

from typing import Protocol


class VectorStore(Protocol):
    """向量存储协议

    定义统一的向量存储接口，便于扩展不同的存储后端。
    """

    def upsert(
        self,
        chatroom_id: str,
        messages: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """插入或更新向量

        Args:
            chatroom_id: 聊天室 ID
            messages: 消息列表，每个消息至少包含 msg_id 和 content
            embeddings: 向量列表，与消息一一对应
        """
        ...

    def search_similar(
        self,
        query_embedding: list[float],
        chatroom_id: str | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """相似性搜索

        Args:
            query_embedding: 查询向量
            chatroom_id: 聊天室 ID（可选，用于过滤）
            top_k: 返回结果数量

        Returns:
            相似消息列表，每个结果包含 msg_id, content, score
        """
        ...

    def get_embeddings(
        self,
        chatroom_id: str,
        message_ids: list[str],
    ) -> list[list[float]]:
        """获取指定消息的向量

        Args:
            chatroom_id: 聊天室 ID
            message_ids: 消息 ID 列表

        Returns:
            向量列表，与消息 ID 一一对应（不存在的 ID 会被跳过）
        """
        ...
