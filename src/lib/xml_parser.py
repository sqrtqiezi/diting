"""微信消息 XML 解析器"""

from dataclasses import dataclass
from xml.etree import ElementTree as ET

import structlog

logger = structlog.get_logger()


@dataclass
class ReferMsg:
    """引用消息结构"""

    svrid: str
    type: int
    content: str
    displayname: str
    createtime: int


@dataclass
class AppmsgContent:
    """App 消息内容"""

    appmsg_type: int
    title: str
    refermsg: ReferMsg | None = None


def parse_appmsg_content(xml_str: str) -> AppmsgContent | None:
    """解析 appmsg XML 内容"""
    if not xml_str or not xml_str.strip():
        return None

    try:
        root = ET.fromstring(xml_str)
        appmsg = root.find("appmsg")
        if appmsg is None:
            return None

        appmsg_type = int(appmsg.findtext("type", "0"))
        title = appmsg.findtext("title", "") or ""
        refermsg = _extract_refermsg(appmsg)

        return AppmsgContent(appmsg_type=appmsg_type, title=title, refermsg=refermsg)
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
