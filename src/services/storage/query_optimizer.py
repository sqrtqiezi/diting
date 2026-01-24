"""
查询优化器: 分区裁剪、谓词下推、列裁剪

提供查询性能优化功能。
"""

from datetime import datetime
from typing import Any

import pyarrow.compute as pc
import structlog

logger = structlog.get_logger()


class QueryOptimizer:
    """查询优化器"""

    @staticmethod
    def optimize_partition_filters(start_date: str, end_date: str) -> list[tuple[str, str, Any]]:
        """
        分区裁剪: 构建最优分区过滤器

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            分区过滤器列表 [(field, op, value), ...]
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        filters = []

        # 年份过滤
        if start_dt.year == end_dt.year:
            filters.append(("year", "=", start_dt.year))
        else:
            filters.append(("year", ">=", start_dt.year))
            filters.append(("year", "<=", end_dt.year))

        # 月份过滤（仅在同一年时应用）
        if start_dt.year == end_dt.year:
            if start_dt.month == end_dt.month:
                filters.append(("month", "=", start_dt.month))
            else:
                filters.append(("month", ">=", start_dt.month))
                filters.append(("month", "<=", end_dt.month))

        # 日期过滤（仅在同一年月时应用）
        if start_dt.year == end_dt.year and start_dt.month == end_dt.month:
            if start_dt.day == end_dt.day:
                filters.append(("day", "=", start_dt.day))
            else:
                filters.append(("day", ">=", start_dt.day))
                filters.append(("day", "<=", end_dt.day))

        logger.debug(
            "Partition filters optimized",
            start_date=start_date,
            end_date=end_date,
            filters=filters,
        )

        return filters

    @staticmethod
    def build_predicate_pushdown_filter(
        partition_filters: list[tuple[str, str, Any]],
        extra_filters: dict[str, Any] | None = None,
    ) -> Any:
        """
        谓词下推: 构建 PyArrow 过滤表达式

        Args:
            partition_filters: 分区过滤器
            extra_filters: 额外过滤条件

        Returns:
            PyArrow 过滤表达式
        """
        expressions = []

        # 添加分区过滤器
        for field, op, value in partition_filters:
            if op == "=":
                expressions.append(pc.field(field) == value)
            elif op == ">=":
                expressions.append(pc.field(field) >= value)
            elif op == "<=":
                expressions.append(pc.field(field) <= value)
            elif op == ">":
                expressions.append(pc.field(field) > value)
            elif op == "<":
                expressions.append(pc.field(field) < value)

        # 添加额外过滤条件
        if extra_filters:
            for field, value in extra_filters.items():
                if isinstance(value, list):
                    # 支持 IN 查询
                    expressions.append(pc.field(field).isin(value))
                else:
                    expressions.append(pc.field(field) == value)

        # 合并所有表达式（AND 逻辑）
        if len(expressions) == 0:
            return None
        elif len(expressions) == 1:
            return expressions[0]
        else:
            result = expressions[0]
            for expr in expressions[1:]:
                result = result & expr

            logger.debug("Predicate pushdown filter built", expression_count=len(expressions))

            return result

    @staticmethod
    def optimize_column_projection(
        requested_columns: list[str] | None, required_columns: list[str] | None = None
    ) -> list[str] | None:
        """
        列裁剪: 优化列投影

        Args:
            requested_columns: 用户请求的列
            required_columns: 必需的列（如分区列）

        Returns:
            优化后的列列表
        """
        if requested_columns is None:
            # 未指定列，返回全部
            return None

        # 合并请求列和必需列
        columns = set(requested_columns)
        if required_columns:
            columns.update(required_columns)

        optimized = list(columns)

        logger.debug(
            "Column projection optimized",
            requested=requested_columns,
            required=required_columns,
            optimized=optimized,
        )

        return optimized

    @staticmethod
    def estimate_scan_cost(
        start_date: str, end_date: str, partition_count: int | None = None
    ) -> dict[str, Any]:
        """
        估算扫描成本

        Args:
            start_date: 开始日期
            end_date: 结束日期
            partition_count: 实际分区数量（None=使用日期范围估算）

        Returns:
            成本估算信息
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # 计算日期范围
        date_range_days = (end_dt - start_dt).days + 1

        # 估算扫描的分区数（如果未提供实际分区数）
        if partition_count is None:
            estimated_partitions = date_range_days
        else:
            estimated_partitions = min(date_range_days, partition_count)

        # 估算扫描成本（简化模型）
        scan_cost = estimated_partitions * 100  # 每分区 100 单位成本

        return {
            "date_range_days": date_range_days,
            "estimated_partitions": estimated_partitions,
            "scan_cost": scan_cost,
            "is_efficient": date_range_days <= 31,  # 月度查询以内认为高效
        }
