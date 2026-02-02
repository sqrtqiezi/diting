"""Embedding 提供者协议

定义 Embedding 模型的统一接口。
"""

from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Embedding 提供者协议

    定义统一的 Embedding 接口，便于扩展不同的 Embedding 实现。
    区分 embed_documents 和 embed_query 方法，部分 Embedding 模型
    （如 E5、BGE）对查询和文档使用不同的前缀处理。
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文档（用于索引）

        某些模型会自动添加 'passage:' 前缀。

        Args:
            texts: 文档文本列表

        Returns:
            向量列表，每个向量对应一个文档
        """
        ...

    def embed_query(self, text: str) -> list[float]:
        """嵌入查询（用于搜索）

        某些模型会自动添加 'query:' 前缀。

        Args:
            text: 查询文本

        Returns:
            查询向量
        """
        ...

    @property
    def dimension(self) -> int:
        """向量维度

        Returns:
            向量的维度数
        """
        ...
