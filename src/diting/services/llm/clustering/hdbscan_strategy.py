"""HDBSCAN 聚类策略实现

使用 HDBSCAN 算法进行密度聚类。
"""

from __future__ import annotations

from collections import defaultdict

import hdbscan
import numpy as np

from diting.services.llm.clustering.strategy import Cluster


class HDBSCANClusteringStrategy:
    """基于 HDBSCAN 的聚类策略

    HDBSCAN (Hierarchical Density-Based Spatial Clustering of Applications with Noise)
    是一种密度聚类算法，能够自动发现不同密度的聚类，并识别噪声点。
    """

    def __init__(
        self,
        min_cluster_size: int = 5,
        min_samples: int = 2,
        metric: str = "euclidean",
        cluster_selection_epsilon: float = 0.0,
    ) -> None:
        """初始化 HDBSCAN 聚类策略

        Args:
            min_cluster_size: 最小聚类大小，聚类至少需要这么多点
            min_samples: 核心点的最小邻居数
            metric: 距离度量方式，默认欧氏距离
            cluster_selection_epsilon: 聚类选择的 epsilon 阈值
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.metric = metric
        self.cluster_selection_epsilon = cluster_selection_epsilon

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
            聚类结果列表，包括噪声点聚类（cluster_id = -1）
        """
        if not embeddings or not message_ids:
            return []

        if len(embeddings) != len(message_ids):
            raise ValueError("embeddings 和 message_ids 长度必须相同")

        # 转换为 numpy 数组
        X = np.array(embeddings)

        # 如果数据点太少，无法进行 HDBSCAN 聚类
        # HDBSCAN 需要至少 min_cluster_size 个点
        if len(X) < self.min_cluster_size:
            # 所有点作为噪声点返回
            return [
                Cluster(
                    cluster_id=-1,
                    message_ids=message_ids,
                    centroid=None,
                )
            ]

        # 执行 HDBSCAN 聚类
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric=self.metric,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
        )
        labels = clusterer.fit_predict(X)

        # 按聚类 ID 分组消息
        cluster_messages: dict[int, list[tuple[int, str]]] = defaultdict(list)
        for idx, (label, msg_id) in enumerate(zip(labels, message_ids, strict=False)):
            # 将 numpy.int64 转换为 Python int
            cluster_messages[int(label)].append((idx, msg_id))

        # 构建聚类结果
        clusters: list[Cluster] = []
        for cluster_id, members in sorted(cluster_messages.items()):
            indices = [idx for idx, _ in members]
            msg_ids = [msg_id for _, msg_id in members]

            # 计算聚类中心（非噪声点）
            centroid = None
            if cluster_id >= 0:
                cluster_vectors = X[indices]
                centroid = cluster_vectors.mean(axis=0).tolist()

            clusters.append(
                Cluster(
                    cluster_id=cluster_id,
                    message_ids=msg_ids,
                    centroid=centroid,
                )
            )

        return clusters
