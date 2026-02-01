"""JSONL 流式读取器

提供高效的 JSONL 文件流式读取功能。
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


def read_jsonl_stream(
    jsonl_path: str | Path, skip_invalid: bool = True, start_line: int = 0
) -> Iterator[dict[str, Any]]:
    """流式读取 JSONL 文件

    逐行读取并解析 JSON，避免一次性加载整个文件到内存。

    Args:
        jsonl_path: JSONL 文件路径
        skip_invalid: 是否跳过无效的 JSON 行（默认 True）
        start_line: 起始行号（用于断点续传，默认 0）

    Yields:
        解析后的消息字典

    Raises:
        FileNotFoundError: 文件不存在
        OSError: 文件读取失败
    """
    jsonl_path = Path(jsonl_path)

    if not jsonl_path.exists():
        logger.error("jsonl_file_not_found", path=str(jsonl_path))
        raise FileNotFoundError(f"JSONL 文件不存在: {jsonl_path}")

    logger.info(
        "reading_jsonl_stream",
        path=str(jsonl_path),
        start_line=start_line,
        skip_invalid=skip_invalid,
    )

    line_number = 0
    valid_count = 0
    invalid_count = 0

    try:
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line_number += 1

                # 跳过起始行之前的内容
                if line_number <= start_line:
                    continue

                # 跳过空行
                line = line.strip()
                if not line:
                    continue

                # 解析 JSON
                try:
                    message = json.loads(line)
                    valid_count += 1
                    yield message
                except json.JSONDecodeError as e:
                    invalid_count += 1
                    logger.warning(
                        "invalid_json_line",
                        line_number=line_number,
                        error=str(e),
                        line_preview=line[:100],
                    )

                    if not skip_invalid:
                        raise

        logger.info(
            "jsonl_stream_completed",
            path=str(jsonl_path),
            total_lines=line_number,
            valid_count=valid_count,
            invalid_count=invalid_count,
        )

    except OSError as e:
        logger.error("jsonl_read_failed", path=str(jsonl_path), error=str(e))
        raise


def count_jsonl_lines(jsonl_path: str | Path) -> int:
    """快速统计 JSONL 文件行数

    Args:
        jsonl_path: JSONL 文件路径

    Returns:
        文件行数

    Raises:
        FileNotFoundError: 文件不存在
    """
    jsonl_path = Path(jsonl_path)

    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL 文件不存在: {jsonl_path}")

    with open(jsonl_path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def read_jsonl_batch(
    jsonl_path: str | Path, batch_size: int = 10_000, skip_invalid: bool = True, start_line: int = 0
) -> Iterator[list[dict[str, Any]]]:
    """批量读取 JSONL 文件

    将消息分批读取，每批包含 batch_size 条消息。

    Args:
        jsonl_path: JSONL 文件路径
        batch_size: 每批消息数量
        skip_invalid: 是否跳过无效的 JSON 行
        start_line: 起始行号

    Yields:
        消息字典列表（每批）

    Raises:
        FileNotFoundError: 文件不存在
        OSError: 文件读取失败
    """
    batch = []

    for message in read_jsonl_stream(jsonl_path, skip_invalid, start_line):
        batch.append(message)

        if len(batch) >= batch_size:
            yield batch
            batch = []

    # 返回最后一批（可能不足 batch_size）
    if batch:
        yield batch
