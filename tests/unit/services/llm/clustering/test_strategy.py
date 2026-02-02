"""ClusteringStrategy Protocol 测试

TDD RED Phase: 先写测试，验证 Protocol 接口设计。
"""


class TestClusterDataclass:
    """Cluster 数据类测试"""

    def test_cluster_has_required_fields(self):
        """测试 Cluster 数据类有必需字段"""
        from diting.services.llm.clustering.strategy import Cluster

        cluster = Cluster(
            cluster_id=0,
            message_ids=["msg_001", "msg_002"],
        )

        assert cluster.cluster_id == 0
        assert cluster.message_ids == ["msg_001", "msg_002"]

    def test_cluster_has_optional_centroid(self):
        """测试 Cluster 数据类有可选的 centroid 字段"""
        from diting.services.llm.clustering.strategy import Cluster

        # 不提供 centroid
        cluster1 = Cluster(cluster_id=0, message_ids=["msg_001"])
        assert cluster1.centroid is None

        # 提供 centroid
        cluster2 = Cluster(
            cluster_id=1,
            message_ids=["msg_002"],
            centroid=[0.1, 0.2, 0.3],
        )
        assert cluster2.centroid == [0.1, 0.2, 0.3]


class TestClusteringStrategyProtocol:
    """ClusteringStrategy Protocol 测试"""

    def test_protocol_has_cluster_method(self):
        """测试 Protocol 定义了 cluster 方法"""
        from diting.services.llm.clustering.strategy import ClusteringStrategy

        assert hasattr(ClusteringStrategy, "cluster")


class MockClusteringStrategy:
    """Mock 聚类策略用于测试 Protocol 兼容性"""

    def cluster(
        self,
        embeddings: list[list[float]],
        message_ids: list[str],
    ) -> list:
        """对向量进行聚类"""
        from diting.services.llm.clustering.strategy import Cluster

        # 简单实现：所有消息归为一个聚类
        if not embeddings:
            return []
        return [Cluster(cluster_id=0, message_ids=message_ids)]


class TestMockClusteringStrategyCompliance:
    """测试 Mock Strategy 符合 Protocol"""

    def test_mock_strategy_is_protocol_compliant(self):
        """测试 Mock Strategy 符合 ClusteringStrategy Protocol"""

        strategy = MockClusteringStrategy()

        # 验证方法存在且可调用
        assert callable(strategy.cluster)

    def test_cluster_returns_list_of_clusters(self):
        """测试 cluster 返回 Cluster 列表"""
        from diting.services.llm.clustering.strategy import Cluster

        strategy = MockClusteringStrategy()
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        message_ids = ["msg_001", "msg_002"]

        clusters = strategy.cluster(embeddings, message_ids)

        assert isinstance(clusters, list)
        assert len(clusters) == 1
        assert isinstance(clusters[0], Cluster)
        assert clusters[0].cluster_id == 0
        assert clusters[0].message_ids == ["msg_001", "msg_002"]

    def test_cluster_handles_empty_input(self):
        """测试 cluster 处理空输入"""
        strategy = MockClusteringStrategy()

        clusters = strategy.cluster([], [])

        assert clusters == []
