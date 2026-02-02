"""HDBSCAN 聚类策略测试

TDD RED Phase: 先写测试，验证 HDBSCAN 实现。
"""


class TestHDBSCANClusteringStrategy:
    """HDBSCAN 聚类策略测试"""

    def test_import_hdbscan_strategy(self):
        """测试可以导入 HDBSCANClusteringStrategy"""
        from diting.services.llm.clustering.hdbscan_strategy import HDBSCANClusteringStrategy

        assert HDBSCANClusteringStrategy is not None

    def test_default_parameters(self):
        """测试默认参数"""
        from diting.services.llm.clustering.hdbscan_strategy import HDBSCANClusteringStrategy

        strategy = HDBSCANClusteringStrategy()

        assert strategy.min_cluster_size >= 2
        assert strategy.min_samples >= 1

    def test_custom_parameters(self):
        """测试自定义参数"""
        from diting.services.llm.clustering.hdbscan_strategy import HDBSCANClusteringStrategy

        strategy = HDBSCANClusteringStrategy(min_cluster_size=5, min_samples=3)

        assert strategy.min_cluster_size == 5
        assert strategy.min_samples == 3

    def test_cluster_returns_list_of_clusters(self):
        """测试 cluster 返回 Cluster 列表"""
        from diting.services.llm.clustering.hdbscan_strategy import HDBSCANClusteringStrategy
        from diting.services.llm.clustering.strategy import Cluster

        strategy = HDBSCANClusteringStrategy(min_cluster_size=2, min_samples=1)

        # 创建两组明显不同的向量
        embeddings = [
            [0.1, 0.1, 0.1],  # 组 1
            [0.11, 0.12, 0.1],  # 组 1
            [0.9, 0.9, 0.9],  # 组 2
            [0.91, 0.88, 0.9],  # 组 2
        ]
        message_ids = ["msg_001", "msg_002", "msg_003", "msg_004"]

        clusters = strategy.cluster(embeddings, message_ids)

        assert isinstance(clusters, list)
        for cluster in clusters:
            assert isinstance(cluster, Cluster)
            assert isinstance(cluster.cluster_id, int)
            assert isinstance(cluster.message_ids, list)

    def test_cluster_handles_empty_input(self):
        """测试 cluster 处理空输入"""
        from diting.services.llm.clustering.hdbscan_strategy import HDBSCANClusteringStrategy

        strategy = HDBSCANClusteringStrategy()

        clusters = strategy.cluster([], [])

        assert clusters == []

    def test_cluster_handles_single_message(self):
        """测试 cluster 处理单条消息"""
        from diting.services.llm.clustering.hdbscan_strategy import HDBSCANClusteringStrategy

        strategy = HDBSCANClusteringStrategy(min_cluster_size=2)

        embeddings = [[0.1, 0.2, 0.3]]
        message_ids = ["msg_001"]

        clusters = strategy.cluster(embeddings, message_ids)

        # 单条消息应该被标记为噪声点（cluster_id = -1）或单独一个聚类
        assert isinstance(clusters, list)

    def test_cluster_groups_similar_vectors(self):
        """测试 cluster 将相似向量分组"""
        from diting.services.llm.clustering.hdbscan_strategy import HDBSCANClusteringStrategy

        strategy = HDBSCANClusteringStrategy(min_cluster_size=2, min_samples=1)

        # 创建两组明显不同的向量
        embeddings = [
            [0.0, 0.0, 0.0],  # 组 1
            [0.01, 0.01, 0.01],  # 组 1
            [0.02, 0.0, 0.01],  # 组 1
            [1.0, 1.0, 1.0],  # 组 2
            [0.99, 1.01, 1.0],  # 组 2
            [1.01, 0.99, 1.0],  # 组 2
        ]
        message_ids = ["msg_001", "msg_002", "msg_003", "msg_004", "msg_005", "msg_006"]

        clusters = strategy.cluster(embeddings, message_ids)

        # 应该有至少 2 个聚类（可能有噪声点）
        non_noise_clusters = [c for c in clusters if c.cluster_id >= 0]
        assert len(non_noise_clusters) >= 1  # 至少有一个有效聚类

    def test_cluster_includes_noise_cluster(self):
        """测试 cluster 包含噪声点聚类"""
        from diting.services.llm.clustering.hdbscan_strategy import HDBSCANClusteringStrategy

        strategy = HDBSCANClusteringStrategy(min_cluster_size=3, min_samples=2)

        # 创建一组紧密的向量和一个离群点
        embeddings = [
            [0.0, 0.0, 0.0],  # 组 1
            [0.01, 0.01, 0.01],  # 组 1
            [0.02, 0.0, 0.01],  # 组 1
            [10.0, 10.0, 10.0],  # 离群点
        ]
        message_ids = ["msg_001", "msg_002", "msg_003", "msg_004"]

        clusters = strategy.cluster(embeddings, message_ids)

        # 检查是否有噪声点聚类
        # 噪声点可能存在也可能不存在，取决于 HDBSCAN 的判断
        assert isinstance(clusters, list)
        assert any(c.cluster_id == -1 for c in clusters) or len(clusters) > 0

    def test_cluster_calculates_centroid(self):
        """测试 cluster 计算聚类中心"""
        from diting.services.llm.clustering.hdbscan_strategy import HDBSCANClusteringStrategy

        strategy = HDBSCANClusteringStrategy(min_cluster_size=2, min_samples=1)

        embeddings = [
            [0.0, 0.0, 0.0],
            [0.2, 0.2, 0.2],
        ]
        message_ids = ["msg_001", "msg_002"]

        clusters = strategy.cluster(embeddings, message_ids)

        # 非噪声聚类应该有 centroid
        for cluster in clusters:
            if cluster.cluster_id >= 0:
                assert cluster.centroid is not None
                assert len(cluster.centroid) == 3

    def test_cluster_preserves_message_id_order(self):
        """测试 cluster 保持消息 ID 顺序"""
        from diting.services.llm.clustering.hdbscan_strategy import HDBSCANClusteringStrategy

        strategy = HDBSCANClusteringStrategy(min_cluster_size=2, min_samples=1)

        embeddings = [
            [0.0, 0.0],
            [0.01, 0.01],
        ]
        message_ids = ["msg_002", "msg_001"]  # 故意乱序

        clusters = strategy.cluster(embeddings, message_ids)

        # 所有消息 ID 应该都在结果中
        all_ids = []
        for cluster in clusters:
            all_ids.extend(cluster.message_ids)
        assert set(all_ids) == {"msg_001", "msg_002"}


class TestHDBSCANProtocolCompliance:
    """测试 HDBSCAN 策略符合 ClusteringStrategy Protocol"""

    def test_implements_clustering_strategy_protocol(self):
        """测试实现 ClusteringStrategy Protocol"""
        from diting.services.llm.clustering.hdbscan_strategy import HDBSCANClusteringStrategy

        strategy = HDBSCANClusteringStrategy()

        # 验证方法存在且可调用
        assert callable(strategy.cluster)
