"""消息增强服务"""

from typing import Any

from src.lib.xml_parser import parse_appmsg_content


def enrich_message(message: dict[str, Any]) -> dict[str, Any]:
    """解析 XML 并添加结构化字段"""
    if message.get("msg_type") != 49:
        return message

    parsed = parse_appmsg_content(str(message.get("content", "")))
    if parsed is None:
        return message

    message["appmsg_type"] = parsed.appmsg_type
    message["appmsg_title"] = parsed.title

    if parsed.appmsg_type == 57 and parsed.refermsg:
        message["refermsg"] = {
            "svrid": parsed.refermsg.svrid,
            "type": parsed.refermsg.type,
            "content": parsed.refermsg.content,
            "displayname": parsed.refermsg.displayname,
            "createtime": parsed.refermsg.createtime,
        }

    return message


def enrich_messages_batch(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量增强消息"""
    return [enrich_message(message) for message in messages]
