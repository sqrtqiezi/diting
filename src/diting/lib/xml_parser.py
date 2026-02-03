"""微信消息 XML 解析器"""

from dataclasses import dataclass
from xml.etree import ElementTree as ET

import structlog

logger = structlog.get_logger()

# 需要过滤的 appmsg 类型
FILTERED_APPMSG_TYPES: frozenset[int] = frozenset({3, 47, 51, 124})


@dataclass
class ReferMsg:
    """引用消息结构"""

    svrid: str
    type: int
    content: str
    displayname: str
    createtime: int


@dataclass
class XmlMessageType:
    """XML 消息类型识别结果"""

    category: str  # "appmsg" | "emoji" | "voicemsg" | "sysmsg" | "op" | "img" | "unknown"
    appmsg_type: int | None = None
    should_filter: bool = False
    filter_reason: str | None = None


@dataclass
class AppmsgContent:
    """App 消息内容"""

    appmsg_type: int
    title: str
    refermsg: ReferMsg | None = None
    des: str | None = None  # 用于 type=5/4 的描述


def identify_xml_message_type(xml_str: str) -> XmlMessageType:
    """识别 XML 消息类型并返回过滤建议

    Args:
        xml_str: XML 字符串

    Returns:
        XmlMessageType 包含类别、appmsg_type 和过滤建议
    """
    if not xml_str or not xml_str.strip():
        return XmlMessageType(category="unknown")

    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return XmlMessageType(category="unknown")

    # 检查 emoji
    if root.find("emoji") is not None:
        return XmlMessageType(category="emoji", should_filter=True, filter_reason="emoji")

    # 检查 voicemsg
    if root.find("voicemsg") is not None:
        return XmlMessageType(
            category="voicemsg", should_filter=True, filter_reason="voicemsg"
        )

    # 检查 sysmsg
    if root.tag == "sysmsg":
        return XmlMessageType(category="sysmsg", should_filter=True, filter_reason="sysmsg")

    # 检查 op (lastMessage 等)
    op_elem = root.find("op")
    if op_elem is not None:
        op_name = op_elem.findtext("name", "")
        if op_name == "lastMessage":
            return XmlMessageType(
                category="op", should_filter=True, filter_reason="op:lastMessage"
            )
        return XmlMessageType(category="op")

    # 检查 appmsg
    appmsg = root.find("appmsg")
    if appmsg is not None:
        appmsg_type = int(appmsg.findtext("type", "0"))

        # 检查需要过滤的 appmsg 类型
        if appmsg_type in FILTERED_APPMSG_TYPES:
            return XmlMessageType(
                category="appmsg",
                appmsg_type=appmsg_type,
                should_filter=True,
                filter_reason=f"appmsg:type={appmsg_type}",
            )

        # 检查 type=1 + refermsg (轻量引用/表态式回复)
        if appmsg_type == 1 and appmsg.find("refermsg") is not None:
            return XmlMessageType(
                category="appmsg",
                appmsg_type=appmsg_type,
                should_filter=True,
                filter_reason="appmsg:type=1+refermsg",
            )

        return XmlMessageType(category="appmsg", appmsg_type=appmsg_type)

    # 检查 img
    if root.find("img") is not None:
        return XmlMessageType(category="img")

    return XmlMessageType(category="unknown")


# 支持 refermsg 提取的 appmsg 类型
REFERMSG_APPMSG_TYPES: frozenset[int] = frozenset({57, 49, 1})

# 支持 des 字段提取的 appmsg 类型 (文章分享)
ARTICLE_APPMSG_TYPES: frozenset[int] = frozenset({4, 5})


def parse_appmsg_content(xml_str: str) -> AppmsgContent | None:
    """解析 appmsg XML 内容

    支持:
    - type=57/49/1: 提取 refermsg 引用消息
    - type=4/5: 提取 des 描述字段 (文章分享)
    """
    if not xml_str or not xml_str.strip():
        return None

    try:
        root = ET.fromstring(xml_str)
        appmsg = root.find("appmsg")
        if appmsg is None:
            return None

        appmsg_type = int(appmsg.findtext("type", "0"))
        title = appmsg.findtext("title", "") or ""

        # 提取 refermsg (type=57/49/1)
        refermsg = None
        if appmsg_type in REFERMSG_APPMSG_TYPES:
            refermsg = _extract_refermsg(appmsg)

        # 提取 des (type=4/5 文章分享)
        des = None
        if appmsg_type in ARTICLE_APPMSG_TYPES:
            des = appmsg.findtext("des", "") or None

        return AppmsgContent(
            appmsg_type=appmsg_type, title=title, refermsg=refermsg, des=des
        )
    except (ET.ParseError, ValueError, TypeError) as exc:
        logger.warning("appmsg_parse_error", error=str(exc))
        return None


def _extract_refermsg(appmsg: ET.Element) -> ReferMsg | None:
    refermsg_elem = appmsg.find("refermsg")
    if refermsg_elem is None:
        return None
    try:
        return ReferMsg(
            svrid=refermsg_elem.findtext("svrid", ""),
            type=int(refermsg_elem.findtext("type", "0")),
            content=refermsg_elem.findtext("content", ""),
            displayname=refermsg_elem.findtext("displayname", ""),
            createtime=int(refermsg_elem.findtext("createtime", "0")),
        )
    except (ValueError, TypeError) as exc:
        logger.warning("refermsg_parse_error", error=str(exc))
        return None
