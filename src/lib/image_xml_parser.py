"""微信图片消息 XML 解析器

解析图片消息的 XML 内容,提取加密密钥和 CDN 地址。
"""

from dataclasses import dataclass
from xml.etree import ElementTree as ET

import structlog

logger = structlog.get_logger()


@dataclass
class ImageInfo:
    """图片信息结构

    Attributes:
        aes_key: AES 解密密钥
        cdn_mid_img_url: CDN 中等尺寸图片 URL (文件 ID)
        md5: 图片 MD5 哈希值 (可选)
        length: 图片文件大小 (可选)
    """

    aes_key: str
    cdn_mid_img_url: str
    md5: str | None = None
    length: int | None = None


def is_encrypted_image_xml(xml_str: str) -> bool:
    """快速检查是否为加密图片消息

    Args:
        xml_str: XML 字符串

    Returns:
        True 如果是加密图片消息
    """
    if not xml_str or not xml_str.strip():
        return False

    content = xml_str.strip()
    # 检查是否以 <msg><img 开头
    if not content.startswith("<msg>"):
        return False

    # 检查是否包含 encryver="1" 表示加密图片
    if 'encryver="1"' not in content and "encryver='1'" not in content:
        return False

    return True


def parse_image_xml(xml_str: str) -> ImageInfo | None:
    """解析图片消息 XML,提取图片信息

    解析微信图片消息的 XML 格式,提取 AES 密钥和 CDN URL。
    仅处理加密图片 (encryver="1")。

    典型的图片 XML 格式:
    <msg>
        <img aeskey="..." cdnmidimgurl="..." encryver="1" .../>
    </msg>

    Args:
        xml_str: 图片消息的 XML 字符串

    Returns:
        ImageInfo 对象,解析失败返回 None
    """
    if not is_encrypted_image_xml(xml_str):
        return None

    try:
        root = ET.fromstring(xml_str.strip())
        img_elem = root.find("img")

        if img_elem is None:
            logger.debug("image_xml_no_img_element", xml=xml_str[:100])
            return None

        # 验证加密版本
        encryver = img_elem.get("encryver")
        if encryver != "1":
            logger.debug("image_xml_not_encrypted", encryver=encryver)
            return None

        # 提取必需字段
        aes_key = img_elem.get("aeskey")
        cdn_mid_img_url = img_elem.get("cdnmidimgurl")

        if not aes_key or not cdn_mid_img_url:
            logger.warning(
                "image_xml_missing_required_fields",
                aes_key=bool(aes_key),
                cdn_mid_img_url=bool(cdn_mid_img_url),
            )
            return None

        # 提取可选字段
        md5 = img_elem.get("md5")
        length_str = img_elem.get("length")
        length = int(length_str) if length_str else None

        return ImageInfo(
            aes_key=aes_key,
            cdn_mid_img_url=cdn_mid_img_url,
            md5=md5,
            length=length,
        )

    except ET.ParseError as exc:
        logger.warning("image_xml_parse_error", error=str(exc), xml=xml_str[:100])
        return None
    except (ValueError, TypeError) as exc:
        logger.warning("image_xml_value_error", error=str(exc))
        return None
