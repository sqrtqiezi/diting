"""
查询服务: 高效查询历史消息

提供基于日期范围和过滤条件的消息查询功能。
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.dataset as ds
import structlog

from .query_optimizer import QueryOptimizer

logger = structlog.get_logger()


def query_messages(
    start_date: str,
    end_date: str,
    parquet_root: str | Path = "data/parquet/messages",
    filters: dict[str, Any] | None = None,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    查询消息记录(支持时间范围和过滤条件)

    Args:
        start_date: 开始日期(YYYY-MM-DD)
        end_date: 结束日期(YYYY-MM-DD)
        parquet_root: Parquet 根目录
        filters: 额外过滤条件 (如 {"chatroom": "xxx", "msg_type": 1})
        columns: 需要的列(None=全部)

    Returns:
        pd.DataFrame: 查询结果

    Raises:
        ValueError: 日期格式无效
        FileNotFoundError: Parquet 目录不存在
    """
    parquet_path = Path(parquet_root)

    # 验证路径存在
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet root not found: {parquet_root}")

    # 解析日期范围
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Invalid date format (expected YYYY-MM-DD): {e}") from e

    # 使用查询优化器构建过滤器
    optimizer = QueryOptimizer()
    partition_filters = optimizer.optimize_partition_filters(start_date, end_date)
    arrow_filters = optimizer.build_predicate_pushdown_filter(partition_filters, filters)
    optimized_columns = optimizer.optimize_column_projection(columns)

    logger.info(
        "Querying messages",
        start_date=start_date,
        end_date=end_date,
        filters=filters,
        columns=columns,
    )

    try:
        # 使用 PyArrow Dataset API 读取分区数据
        dataset = ds.dataset(str(parquet_path), format="parquet", partitioning="hive")

        # 读取数据（带分区裁剪和谓词下推）
        table = dataset.to_table(filter=arrow_filters, columns=optimized_columns)

        # 转换为 Pandas DataFrame
        df = table.to_pandas()

        # 精确过滤时间戳（分区过滤可能包含边界外的数据）
        if len(df) > 0 and "create_time" in df.columns:
            start_ts = int(start_dt.timestamp())
            end_ts = int(end_dt.replace(hour=23, minute=59, second=59).timestamp())
            df = df[(df["create_time"] >= start_ts) & (df["create_time"] <= end_ts)]

        logger.info("Query completed", result_count=len(df))

        return df

    except Exception as e:
        logger.error("Query failed", error=str(e))
        raise


def query_messages_by_id(
    msg_ids: list[str],
    parquet_root: str | Path = "data/parquet/messages",
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    根据 msg_id 查询消息

    Args:
        msg_ids: 消息 ID 列表
        parquet_root: Parquet 根目录
        columns: 需要的列(None=全部)

    Returns:
        pd.DataFrame: 查询结果
    """
    parquet_path = Path(parquet_root)

    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet root not found: {parquet_root}")

    logger.info("Querying messages by ID", msg_ids=msg_ids, columns=columns)

    try:
        # 使用 PyArrow Dataset API
        dataset = ds.dataset(str(parquet_path), format="parquet", partitioning="hive")

        # 构建 msg_id 过滤器
        import pyarrow.compute as pc

        msg_id_filter = pc.field("msg_id").isin(msg_ids)

        # 读取数据
        table = dataset.to_table(filter=msg_id_filter, columns=columns)

        # 转换为 DataFrame
        df = table.to_pandas()

        logger.info("Query by ID completed", result_count=len(df))

        return df

    except Exception as e:
        logger.error("Query by ID failed", error=str(e))
        raise
