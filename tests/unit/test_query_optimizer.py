"""
单元测试: QueryOptimizer 查询优化器

测试查询优化器的各项功能。
"""


from src.services.storage.query_optimizer import QueryOptimizer


class TestQueryOptimizer:
    """QueryOptimizer 单元测试"""

    def test_optimize_partition_filters_same_day(self):
        """测试同一天的分区过滤"""
        optimizer = QueryOptimizer()
        filters = optimizer.optimize_partition_filters("2026-01-23", "2026-01-23")

        assert ("year", "=", 2026) in filters
        assert ("month", "=", 1) in filters
        assert ("day", "=", 23) in filters

    def test_optimize_partition_filters_same_month(self):
        """测试同一月的分区过滤"""
        optimizer = QueryOptimizer()
        filters = optimizer.optimize_partition_filters("2026-01-20", "2026-01-25")

        assert ("year", "=", 2026) in filters
        assert ("month", "=", 1) in filters
        assert ("day", ">=", 20) in filters
        assert ("day", "<=", 25) in filters

    def test_optimize_partition_filters_different_months(self):
        """测试跨月的分区过滤"""
        optimizer = QueryOptimizer()
        filters = optimizer.optimize_partition_filters("2026-01-20", "2026-02-10")

        assert ("year", "=", 2026) in filters
        assert ("month", ">=", 1) in filters
        assert ("month", "<=", 2) in filters

    def test_optimize_partition_filters_different_years(self):
        """测试跨年的分区过滤"""
        optimizer = QueryOptimizer()
        filters = optimizer.optimize_partition_filters("2025-12-20", "2026-01-10")

        assert ("year", ">=", 2025) in filters
        assert ("year", "<=", 2026) in filters

    def test_build_predicate_pushdown_filter_empty(self):
        """测试空过滤条件"""
        optimizer = QueryOptimizer()
        result = optimizer.build_predicate_pushdown_filter([])

        assert result is None

    def test_build_predicate_pushdown_filter_single(self):
        """测试单个过滤条件"""
        optimizer = QueryOptimizer()
        filters = [("year", "=", 2026)]
        result = optimizer.build_predicate_pushdown_filter(filters)

        assert result is not None

    def test_build_predicate_pushdown_filter_multiple(self):
        """测试多个过滤条件"""
        optimizer = QueryOptimizer()
        filters = [
            ("year", "=", 2026),
            ("month", "=", 1),
            ("day", ">=", 20),
        ]
        result = optimizer.build_predicate_pushdown_filter(filters)

        assert result is not None

    def test_build_predicate_pushdown_filter_with_extra(self):
        """测试带额外过滤条件"""
        optimizer = QueryOptimizer()
        partition_filters = [("year", "=", 2026)]
        extra_filters = {"chatroom": "chatroom_123", "msg_type": 1}

        result = optimizer.build_predicate_pushdown_filter(partition_filters, extra_filters)

        assert result is not None

    def test_build_predicate_pushdown_filter_with_list_value(self):
        """测试 IN 查询"""
        optimizer = QueryOptimizer()
        partition_filters = []
        extra_filters = {"msg_type": [1, 2, 3]}

        result = optimizer.build_predicate_pushdown_filter(partition_filters, extra_filters)

        assert result is not None

    def test_optimize_column_projection_none(self):
        """测试无列裁剪"""
        optimizer = QueryOptimizer()
        result = optimizer.optimize_column_projection(None)

        assert result is None

    def test_optimize_column_projection_basic(self):
        """测试基本列裁剪"""
        optimizer = QueryOptimizer()
        result = optimizer.optimize_column_projection(["msg_id", "content"])

        assert set(result) == {"msg_id", "content"}

    def test_optimize_column_projection_with_required(self):
        """测试带必需列的列裁剪"""
        optimizer = QueryOptimizer()
        result = optimizer.optimize_column_projection(
            ["msg_id", "content"], required_columns=["create_time"]
        )

        assert set(result) == {"msg_id", "content", "create_time"}

    def test_estimate_scan_cost_single_day(self):
        """测试单日扫描成本估算"""
        optimizer = QueryOptimizer()
        result = optimizer.estimate_scan_cost("2026-01-23", "2026-01-23")

        assert result["date_range_days"] == 1
        assert result["estimated_partitions"] == 1
        assert result["is_efficient"] is True

    def test_estimate_scan_cost_month(self):
        """测试月度扫描成本估算"""
        optimizer = QueryOptimizer()
        result = optimizer.estimate_scan_cost("2026-01-01", "2026-01-31")

        assert result["date_range_days"] == 31
        assert result["estimated_partitions"] == 31
        assert result["is_efficient"] is True

    def test_estimate_scan_cost_large_range(self):
        """测试大范围扫描成本估算"""
        optimizer = QueryOptimizer()
        result = optimizer.estimate_scan_cost("2026-01-01", "2026-03-31")

        assert result["date_range_days"] == 90
        assert result["is_efficient"] is False  # 超过 31 天
