"""LLM 响应解析器（分隔符 + 键值行协议）"""

from __future__ import annotations

import re
from typing import Any

RESULT_START = "<<<RESULT_START>>>"
RESULT_END = "<<<RESULT_END>>>"
TOPIC_START = "<<<TOPIC>>>"

LIST_FIELDS = {"participants", "message_ids", "message_indices", "keywords"}
FIELD_ALIASES = {
    "topic_title": "title",
    "topic_summary": "summary",
}


def parse_topics_from_text(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    content = _strip_envelope(text)
    if TOPIC_START not in content:
        return [], ["no_topic_blocks_found"]

    topics: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    current_key: str | None = None
    list_mode = False

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == TOPIC_START:
            _finalize_topic(current, topics)
            current = {}
            current_key = None
            list_mode = False
            continue
        if line == RESULT_END:
            break
        if line.startswith("META"):
            current_key = None
            list_mode = False
            continue

        match = re.match(r"^([A-Za-z_]+)\s*:\s*(.*)$", line)
        if match:
            key = match.group(1).lower()
            key = FIELD_ALIASES.get(key, key)
            value = match.group(2).strip()
            current_key = key
            if key in LIST_FIELDS:
                current.setdefault(key, [])
                if value:
                    current[key].extend(_split_list(value))
                list_mode = True
            else:
                current[key] = value
                list_mode = False
            continue

        if list_mode and current_key in LIST_FIELDS and line.startswith("- "):
            item = line[2:].strip()
            if item:
                current.setdefault(current_key, []).append(item)
            continue

        if current_key:
            if current_key in LIST_FIELDS:
                current.setdefault(current_key, []).append(line)
            else:
                current[current_key] = f"{current.get(current_key, '')} {line}".strip()

    _finalize_topic(current, topics)
    if not topics:
        warnings.append("no_topics_parsed")
    return topics, warnings


def _strip_envelope(text: str) -> str:
    if RESULT_START in text:
        text = text.split(RESULT_START, 1)[1]
    if RESULT_END in text:
        text = text.split(RESULT_END, 1)[0]
    return text


def _finalize_topic(current: dict[str, Any], topics: list[dict[str, Any]]) -> None:
    if not current:
        return
    title = current.get("title") or "未命名话题"
    category = current.get("category") or "其他"
    summary = (current.get("summary") or "").strip()
    time_range = (current.get("time_range") or "").strip()
    participants = _ensure_list(current.get("participants"))
    message_ids = _ensure_list(current.get("message_ids"))
    message_indices = _ensure_list(current.get("message_indices"))
    keywords = _ensure_list(current.get("keywords"))
    message_count = _parse_int(current.get("message_count"), default=len(message_ids))
    confidence = _parse_float(current.get("confidence"), default=1.0)
    notes = (current.get("notes") or "").strip()

    topics.append(
        {
            "title": title,
            "category": category,
            "summary": summary,
            "time_range": time_range,
            "participants": participants,
            "message_count": max(0, message_count),
            "keywords": keywords,
            "message_ids": message_ids,
            "message_indices": message_indices,
            "confidence": confidence,
            "notes": notes,
        }
    )


def _ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return _split_list(str(value))


def _split_list(value: str) -> list[str]:
    cleaned = value.strip()
    if not cleaned:
        return []
    parts = re.split(r"[,\uFF0C]", cleaned)
    items = []
    for part in parts:
        item = part.strip().strip('"').strip("'")
        if item:
            items.append(item)
    return items


def _parse_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
