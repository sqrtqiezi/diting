from diting.lib.xml_parser import (
    identify_xml_message_type,
    parse_appmsg_content,
)


class TestIdentifyXmlMessageType:
    """identify_xml_message_type 函数测试"""

    def test_identify_emoji(self) -> None:
        xml = '<msg><emoji md5="abc123" /></msg>'
        result = identify_xml_message_type(xml)
        assert result.category == "emoji"
        assert result.should_filter is True
        assert result.filter_reason == "emoji"

    def test_identify_voicemsg(self) -> None:
        xml = '<msg><voicemsg length="5000" /></msg>'
        result = identify_xml_message_type(xml)
        assert result.category == "voicemsg"
        assert result.should_filter is True
        assert result.filter_reason == "voicemsg"

    def test_identify_sysmsg(self) -> None:
        xml = '<sysmsg type="revokemsg"><revokemsg>...</revokemsg></sysmsg>'
        result = identify_xml_message_type(xml)
        assert result.category == "sysmsg"
        assert result.should_filter is True
        assert result.filter_reason == "sysmsg"

    def test_identify_op_lastmessage(self) -> None:
        xml = "<msg><op><name>lastMessage</name></op></msg>"
        result = identify_xml_message_type(xml)
        assert result.category == "op"
        assert result.should_filter is True
        assert result.filter_reason == "op:lastMessage"

    def test_identify_op_other(self) -> None:
        xml = "<msg><op><name>otherOp</name></op></msg>"
        result = identify_xml_message_type(xml)
        assert result.category == "op"
        assert result.should_filter is False

    def test_identify_appmsg_type_3(self) -> None:
        xml = "<msg><appmsg><type>3</type></appmsg></msg>"
        result = identify_xml_message_type(xml)
        assert result.category == "appmsg"
        assert result.appmsg_type == 3
        assert result.should_filter is True
        assert result.filter_reason == "appmsg:type=3"

    def test_identify_appmsg_type_124(self) -> None:
        xml = "<msg><appmsg><type>124</type></appmsg></msg>"
        result = identify_xml_message_type(xml)
        assert result.category == "appmsg"
        assert result.appmsg_type == 124
        assert result.should_filter is True
        assert result.filter_reason == "appmsg:type=124"

    def test_identify_appmsg_type_1_with_refermsg(self) -> None:
        xml = (
            "<msg><appmsg><type>1</type>"
            "<refermsg><svrid>123</svrid></refermsg>"
            "</appmsg></msg>"
        )
        result = identify_xml_message_type(xml)
        assert result.category == "appmsg"
        assert result.appmsg_type == 1
        assert result.should_filter is True
        assert result.filter_reason == "appmsg:type=1+refermsg"

    def test_identify_appmsg_type_57_not_filtered(self) -> None:
        xml = "<msg><appmsg><type>57</type></appmsg></msg>"
        result = identify_xml_message_type(xml)
        assert result.category == "appmsg"
        assert result.appmsg_type == 57
        assert result.should_filter is False

    def test_identify_img(self) -> None:
        xml = '<msg><img aeskey="abc" /></msg>'
        result = identify_xml_message_type(xml)
        assert result.category == "img"
        assert result.should_filter is False

    def test_identify_unknown(self) -> None:
        xml = "<msg><unknown /></msg>"
        result = identify_xml_message_type(xml)
        assert result.category == "unknown"
        assert result.should_filter is False

    def test_identify_empty_string(self) -> None:
        result = identify_xml_message_type("")
        assert result.category == "unknown"

    def test_identify_malformed_xml(self) -> None:
        result = identify_xml_message_type("<invalid>")
        assert result.category == "unknown"


class TestParseAppmsgContent:
    """parse_appmsg_content 函数测试"""

    def test_parse_refermsg_success(self) -> None:
        xml = (
            "<msg>"
            "<appmsg>"
            "<title>回复内容</title>"
            "<type>57</type>"
            "<refermsg>"
            "<svrid>123456</svrid>"
            "<type>1</type>"
            "<content>原始消息</content>"
            "<displayname>Alice</displayname>"
            "<createtime>1769175533</createtime>"
            "</refermsg>"
            "</appmsg>"
            "</msg>"
        )

        result = parse_appmsg_content(xml)

        assert result is not None
        assert result.appmsg_type == 57
        assert result.title == "回复内容"
        assert result.refermsg is not None
        assert result.refermsg.svrid == "123456"
        assert result.refermsg.displayname == "Alice"

    def test_parse_refermsg_type_49(self) -> None:
        xml = (
            "<msg><appmsg><type>49</type><title>转发</title>"
            "<refermsg><svrid>789</svrid><type>1</type>"
            "<content>被引用内容</content><displayname>Bob</displayname>"
            "<createtime>1769175533</createtime></refermsg>"
            "</appmsg></msg>"
        )
        result = parse_appmsg_content(xml)
        assert result is not None
        assert result.appmsg_type == 49
        assert result.refermsg is not None
        assert result.refermsg.displayname == "Bob"

    def test_parse_refermsg_type_1(self) -> None:
        xml = (
            "<msg><appmsg><type>1</type><title>🫡</title>"
            "<refermsg><svrid>456</svrid><type>1</type>"
            "<content>原消息</content><displayname>Carol</displayname>"
            "<createtime>1769175533</createtime></refermsg>"
            "</appmsg></msg>"
        )
        result = parse_appmsg_content(xml)
        assert result is not None
        assert result.appmsg_type == 1
        assert result.refermsg is not None
        assert result.refermsg.displayname == "Carol"

    def test_parse_article_type_5(self) -> None:
        xml = (
            "<msg><appmsg><type>5</type>"
            "<title>文章标题</title>"
            "<des>文章描述内容</des>"
            "</appmsg></msg>"
        )
        result = parse_appmsg_content(xml)
        assert result is not None
        assert result.appmsg_type == 5
        assert result.title == "文章标题"
        assert result.des == "文章描述内容"

    def test_parse_article_type_4(self) -> None:
        xml = (
            "<msg><appmsg><type>4</type>"
            "<title>视频标题</title>"
            "<des>视频描述</des>"
            "</appmsg></msg>"
        )
        result = parse_appmsg_content(xml)
        assert result is not None
        assert result.appmsg_type == 4
        assert result.title == "视频标题"
        assert result.des == "视频描述"

    def test_parse_no_des_for_other_types(self) -> None:
        xml = "<msg><appmsg><type>57</type><title>回复</title></appmsg></msg>"
        result = parse_appmsg_content(xml)
        assert result is not None
        assert result.appmsg_type == 57
        assert result.des is None

    def test_parse_malformed_xml(self) -> None:
        assert parse_appmsg_content("<invalid>") is None

    def test_parse_empty_content(self) -> None:
        assert parse_appmsg_content("") is None
