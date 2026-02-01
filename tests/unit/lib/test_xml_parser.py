from diting.lib.xml_parser import parse_appmsg_content


def test_parse_refermsg_success() -> None:
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


def test_parse_malformed_xml() -> None:
    assert parse_appmsg_content("<invalid>") is None


def test_parse_empty_content() -> None:
    assert parse_appmsg_content("") is None
