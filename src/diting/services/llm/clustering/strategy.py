"""聚类策略协议

定义聚类算法的统一接口。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Cluster:
    """聚类结果

    Attributes:
        cluster_id: 聚类 ID，-1 表示噪声点
        message_ids: 属于该聚类的消息 ID 列表
        centroid: 聚类中心向量（可选）
    """

    cluster_id: int
    message_ids: list[str]
    centroid: list[float] | None = field(default=None)


class ClusteringStrategy(Protocol):
    """聚类策略协议

    定义统一的聚类接口，便于扩展不同的聚类算法。
    """

    def cluster(
        self,
        embeddings: list[list[float]],
        message_ids: list[str],
    ) -> list[Cluster]:
        """对向量进行聚类

        Args:
            embeddings: 向量列表
            message_ids: 消息 ID 列表，与向量一一对应

        Returns:
            聚类结果列表
        """
        ...
