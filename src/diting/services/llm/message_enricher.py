"""消息增强服务"""

from typing import Any

from diting.lib.xml_parser import (
    REFERMSG_APPMSG_TYPES,
    identify_xml_message_type,
    parse_appmsg_content,
)


def enrich_message(message: dict[str, Any]) -> dict[str, Any]:
    """解析 XML 并添加结构化字段

    对于 msg_type=49 的消息:
    - 识别 XML 消息类型并添加过滤标记
    - 解析 appmsg 内容并提取结构化字段
    - 支持 refermsg 提取 (type=57/49/1)
    - 支持文章分享 des 提取 (type=4/5)
    """
    if message.get("msg_type") != 49:
        return message

    content = str(message.get("content", ""))

    # 识别消息类型并添加过滤标记
    xml_type = identify_xml_message_type(content)
    if xml_type.should_filter:
        message["_should_filter"] = True
        message["_filter_reason"] = xml_type.filter_reason
        return message

    # 解析 appmsg 内容
    parsed = parse_appmsg_content(content)
    if parsed is None:
        return message

    message["appmsg_type"] = parsed.appmsg_type
    message["appmsg_title"] = parsed.title

    # 提取 refermsg (type=57/49/1)
    if parsed.appmsg_type in REFERMSG_APPMSG_TYPES and parsed.refermsg:
        message["refermsg"] = {
            "svrid": parsed.refermsg.svrid,
            "type": parsed.refermsg.type,
            "content": parsed.refermsg.content,
            "displayname": parsed.refermsg.displayname,
            "createtime": parsed.refermsg.createtime,
        }

    # 提取文章分享描述 (type=4/5)
    if parsed.des:
        message["appmsg_des"] = parsed.des

    return message


def enrich_messages_batch(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量增强消息"""
    return [enrich_message(message) for message in messages]
