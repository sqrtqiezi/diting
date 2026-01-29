"""图片 XML 解析器单元测试"""


from src.lib.image_xml_parser import ImageInfo, is_encrypted_image_xml, parse_image_xml


class TestIsEncryptedImageXml:
    """is_encrypted_image_xml 函数测试"""

    def test_valid_encrypted_image(self):
        """测试有效的加密图片 XML"""
        xml = '<msg><img aeskey="abc123" cdnmidimgurl="30xxx" encryver="1"/></msg>'
        assert is_encrypted_image_xml(xml) is True

    def test_valid_encrypted_image_single_quotes(self):
        """测试单引号格式"""
        xml = "<msg><img aeskey='abc123' cdnmidimgurl='30xxx' encryver='1'/></msg>"
        assert is_encrypted_image_xml(xml) is True

    def test_empty_string(self):
        """测试空字符串"""
        assert is_encrypted_image_xml("") is False
        assert is_encrypted_image_xml("   ") is False

    def test_non_msg_xml(self):
        """测试非 msg 根元素"""
        xml = '<root><img aeskey="abc123" cdnmidimgurl="30xxx" encryver="1"/></root>'
        assert is_encrypted_image_xml(xml) is False

    def test_non_encrypted_image(self):
        """测试非加密图片 (encryver != 1)"""
        xml = '<msg><img aeskey="abc123" cdnmidimgurl="30xxx" encryver="0"/></msg>'
        assert is_encrypted_image_xml(xml) is False

    def test_no_encryver(self):
        """测试缺少 encryver 属性"""
        xml = '<msg><img aeskey="abc123" cdnmidimgurl="30xxx"/></msg>'
        assert is_encrypted_image_xml(xml) is False

    def test_text_message(self):
        """测试文本消息"""
        xml = "Hello World"
        assert is_encrypted_image_xml(xml) is False


class TestParseImageXml:
    """parse_image_xml 函数测试"""

    def test_valid_image_xml(self):
        """测试解析有效的图片 XML"""
        xml = """<msg>
            <img aeskey="test_aes_key_123"
                 cdnmidimgurl="30_1234567890_abcdef"
                 encryver="1"
                 md5="d41d8cd98f00b204e9800998ecf8427e"
                 length="12345"/>
        </msg>"""

        result = parse_image_xml(xml)

        assert result is not None
        assert result.aes_key == "test_aes_key_123"
        assert result.cdn_mid_img_url == "30_1234567890_abcdef"
        assert result.md5 == "d41d8cd98f00b204e9800998ecf8427e"
        assert result.length == 12345

    def test_minimal_image_xml(self):
        """测试最小化图片 XML (只有必需字段)"""
        xml = '<msg><img aeskey="key123" cdnmidimgurl="30xxx" encryver="1"/></msg>'

        result = parse_image_xml(xml)

        assert result is not None
        assert result.aes_key == "key123"
        assert result.cdn_mid_img_url == "30xxx"
        assert result.md5 is None
        assert result.length is None

    def test_whitespace_handling(self):
        """测试首尾空白处理"""
        xml = '  \n  <msg><img aeskey="key" cdnmidimgurl="url" encryver="1"/></msg>  \n  '

        result = parse_image_xml(xml)

        assert result is not None
        assert result.aes_key == "key"

    def test_empty_string(self):
        """测试空字符串"""
        assert parse_image_xml("") is None
        assert parse_image_xml("   ") is None

    def test_invalid_xml(self):
        """测试无效 XML"""
        assert parse_image_xml("<msg><unclosed") is None

    def test_missing_img_element(self):
        """测试缺少 img 元素"""
        xml = "<msg><text>Hello</text></msg>"
        assert parse_image_xml(xml) is None

    def test_non_encrypted_image(self):
        """测试非加密图片"""
        xml = '<msg><img aeskey="key" cdnmidimgurl="url" encryver="0"/></msg>'
        assert parse_image_xml(xml) is None

    def test_missing_aes_key(self):
        """测试缺少 aeskey 属性"""
        xml = '<msg><img cdnmidimgurl="30xxx" encryver="1"/></msg>'
        assert parse_image_xml(xml) is None

    def test_missing_cdn_url(self):
        """测试缺少 cdnmidimgurl 属性"""
        xml = '<msg><img aeskey="key123" encryver="1"/></msg>'
        assert parse_image_xml(xml) is None

    def test_empty_aes_key(self):
        """测试空的 aeskey"""
        xml = '<msg><img aeskey="" cdnmidimgurl="30xxx" encryver="1"/></msg>'
        assert parse_image_xml(xml) is None

    def test_invalid_length(self):
        """测试无效的 length 值"""
        xml = '<msg><img aeskey="key" cdnmidimgurl="url" encryver="1" length="not_a_number"/></msg>'
        assert parse_image_xml(xml) is None


class TestImageInfo:
    """ImageInfo dataclass 测试"""

    def test_create_with_required_fields(self):
        """测试仅必需字段创建"""
        info = ImageInfo(aes_key="key", cdn_mid_img_url="url")

        assert info.aes_key == "key"
        assert info.cdn_mid_img_url == "url"
        assert info.md5 is None
        assert info.length is None

    def test_create_with_all_fields(self):
        """测试所有字段创建"""
        info = ImageInfo(
            aes_key="key",
            cdn_mid_img_url="url",
            md5="abc123",
            length=1000,
        )

        assert info.aes_key == "key"
        assert info.cdn_mid_img_url == "url"
        assert info.md5 == "abc123"
        assert info.length == 1000

    def test_equality(self):
        """测试相等性比较"""
        info1 = ImageInfo(aes_key="key", cdn_mid_img_url="url")
        info2 = ImageInfo(aes_key="key", cdn_mid_img_url="url")

        assert info1 == info2
