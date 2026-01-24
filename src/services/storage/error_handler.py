"""错误处理服务

提供格式错误消息的跳过和记录功能。
"""

import json
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class ErrorHandler:
    """错误处理器

    处理格式错误的消息，记录错误并继续处理。
    """

    def __init__(self, error_log_path: str | Path):
        """初始化错误处理器

        Args:
            error_log_path: 错误日志文件路径
        """
        self.error_log_path = Path(error_log_path)
        self.error_log_path.parent.mkdir(parents=True, exist_ok=True)

    def handle_parse_error(
        self, raw_data: str, error: Exception, line_number: int | None = None
    ) -> None:
        """处理解析错误

        Args:
            raw_data: 原始数据
            error: 异常对象
            line_number: 行号（可选）
        """
        error_entry = {
            "error_type": "parse_error",
            "error_message": str(error),
            "line_number": line_number,
            "raw_data": raw_data[:500],  # 只记录前 500 字符
            "timestamp": logger._context.get("timestamp", ""),
        }

        self._log_error(error_entry)

        logger.warning(
            "parse_error_skipped",
            line_number=line_number,
            error=str(error),
            raw_data_preview=raw_data[:100],
        )

    def handle_validation_error(
        self, message: dict[str, Any], error: Exception, msg_id: str | None = None
    ) -> None:
        """处理验证错误

        Args:
            message: 消息字典
            error: 异常对象
            msg_id: 消息 ID（可选）
        """
        error_entry = {
            "error_type": "validation_error",
            "error_message": str(error),
            "msg_id": msg_id,
            "message": message,
            "timestamp": logger._context.get("timestamp", ""),
        }

        self._log_error(error_entry)

        logger.warning("validation_error_skipped", msg_id=msg_id, error=str(error), message=message)

    def handle_schema_error(
        self, message: dict[str, Any], error: Exception, expected_fields: list[str]
    ) -> None:
        """处理 schema 错误

        Args:
            message: 消息字典
            error: 异常对象
            expected_fields: 期望的字段列表
        """
        missing_fields = [field for field in expected_fields if field not in message]

        error_entry = {
            "error_type": "schema_error",
            "error_message": str(error),
            "missing_fields": missing_fields,
            "message_fields": list(message.keys()),
            "message": message,
            "timestamp": logger._context.get("timestamp", ""),
        }

        self._log_error(error_entry)

        logger.warning(
            "schema_error_skipped",
            missing_fields=missing_fields,
            error=str(error),
            message=message,
        )

    def _log_error(self, error_entry: dict[str, Any]) -> None:
        """记录错误到文件

        Args:
            error_entry: 错误条目
        """
        with open(self.error_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(error_entry, ensure_ascii=False) + "\n")

    def get_error_count(self) -> int:
        """获取错误总数

        Returns:
            错误总数
        """
        if not self.error_log_path.exists():
            return 0

        with open(self.error_log_path, encoding="utf-8") as f:
            return sum(1 for _ in f)

    def get_errors_by_type(self) -> dict[str, int]:
        """按类型统计错误

        Returns:
            错误类型统计字典
        """
        if not self.error_log_path.exists():
            return {}

        error_counts: dict[str, int] = {}

        with open(self.error_log_path, encoding="utf-8") as f:
            for line in f:
                try:
                    error_entry = json.loads(line)
                    error_type = error_entry.get("error_type", "unknown")
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
                except json.JSONDecodeError:
                    continue

        return error_counts


def safe_parse_message(
    raw_data: str, error_handler: ErrorHandler | None = None, line_number: int | None = None
) -> dict[str, Any] | None:
    """安全解析消息

    Args:
        raw_data: 原始 JSON 字符串
        error_handler: 错误处理器（可选）
        line_number: 行号（可选）

    Returns:
        解析后的消息字典，如果解析失败则返回 None
    """
    try:
        message: dict[str, Any] = json.loads(raw_data)
        return message
    except json.JSONDecodeError as e:
        if error_handler:
            error_handler.handle_parse_error(raw_data, e, line_number)
        return None


def validate_required_fields(
    message: dict[str, Any],
    required_fields: list[str],
    error_handler: ErrorHandler | None = None,
) -> bool:
    """验证必需字段

    Args:
        message: 消息字典
        required_fields: 必需字段列表
        error_handler: 错误处理器（可选）

    Returns:
        是否通过验证
    """
    missing_fields = [field for field in required_fields if field not in message]

    if missing_fields:
        if error_handler:
            error = ValueError(f"缺少必需字段: {', '.join(missing_fields)}")
            error_handler.handle_schema_error(message, error, required_fields)
        return False

    return True
