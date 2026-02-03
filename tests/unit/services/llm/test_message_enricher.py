"""message_enricher 模块单元测试"""

from diting.services.llm.message_enricher import enrich_message, enrich_messages_batch


class TestEnrichMessage:
    """enrich_message 函数测试"""

    def test_skip_non_appmsg(self) -> None:
        """非 msg_type=49 的消息不处理"""
        message = {"msg_type": 1, "content": "普通文本"}
        result = enrich_message(message)
        assert "_should_filter" not in result
        assert "appmsg_type" not in result

    def test_filter_emoji(self) -> None:
        """emoji 消息应被标记过滤"""
        message = {
            "msg_type": 49,
            "content": '<msg><emoji md5="abc123" /></msg>',
        }
        result = enrich_message(message)
        assert result["_should_filter"] is True
        assert result["_filter_reason"] == "emoji"

    def test_filter_voicemsg(self) -> None:
        """语音消息应被标记过滤"""
        message = {
            "msg_type": 49,
            "content": '<msg><voicemsg length="5000" /></msg>',
        }
        result = enrich_message(message)
        assert result["_should_filter"] is True
        assert result["_filter_reason"] == "voicemsg"

    def test_filter_sysmsg(self) -> None:
        """系统消息应被标记过滤"""
        message = {
            "msg_type": 49,
            "content": '<sysmsg type="revokemsg"><revokemsg>...</revokemsg></sysmsg>',
        }
        result = enrich_message(message)
        assert result["_should_filter"] is True
        assert result["_filter_reason"] == "sysmsg"

    def test_filter_appmsg_type_124(self) -> None:
        """appmsg type=124 应被标记过滤"""
        message = {
            "msg_type": 49,
            "content": "<msg><appmsg><type>124</type></appmsg></msg>",
        }
        result = enrich_message(message)
        assert result["_should_filter"] is True
        assert result["_filter_reason"] == "appmsg:type=124"

    def test_filter_appmsg_type_1_with_refermsg(self) -> None:
        """appmsg type=1 + refermsg 应被标记过滤"""
        message = {
            "msg_type": 49,
            "content": (
                "<msg><appmsg><type>1</type>"
                "<refermsg><svrid>123</svrid></refermsg>"
                "</appmsg></msg>"
            ),
        }
        result = enrich_message(message)
        assert result["_should_filter"] is True
        assert result["_filter_reason"] == "appmsg:type=1+refermsg"

    def test_enrich_refermsg_type_57(self) -> None:
        """type=57 应提取 refermsg"""
        message = {
            "msg_type": 49,
            "content": (
                "<msg><appmsg><type>57</type><title>回复</title>"
                "<refermsg><svrid>123</svrid><type>1</type>"
                "<content>原消息</content><displayname>Alice</displayname>"
                "<createtime>1769175533</createtime></refermsg>"
                "</appmsg></msg>"
            ),
        }
        result = enrich_message(message)
        assert "_should_filter" not in result
        assert result["appmsg_type"] == 57
        assert result["appmsg_title"] == "回复"
        assert result["refermsg"]["displayname"] == "Alice"

    def test_enrich_refermsg_type_49(self) -> None:
        """type=49 应提取 refermsg"""
        message = {
            "msg_type": 49,
            "content": (
                "<msg><appmsg><type>49</type><title>转发</title>"
                "<refermsg><svrid>456</svrid><type>1</type>"
                "<content>被引用</content><displayname>Bob</displayname>"
                "<createtime>1769175533</createtime></refermsg>"
                "</appmsg></msg>"
            ),
        }
        result = enrich_message(message)
        assert result["appmsg_type"] == 49
        assert result["refermsg"]["displayname"] == "Bob"

    def test_enrich_article_type_5(self) -> None:
        """type=5 应提取 des"""
        message = {
            "msg_type": 49,
            "content": (
                "<msg><appmsg><type>5</type>"
                "<title>文章标题</title>"
                "<des>文章描述</des>"
                "</appmsg></msg>"
            ),
        }
        result = enrich_message(message)
        assert result["appmsg_type"] == 5
        assert result["appmsg_title"] == "文章标题"
        assert result["appmsg_des"] == "文章描述"

    def test_enrich_article_type_4(self) -> None:
        """type=4 应提取 des"""
        message = {
            "msg_type": 49,
            "content": (
                "<msg><appmsg><type>4</type>"
                "<title>视频标题</title>"
                "<des>视频描述</des>"
                "</appmsg></msg>"
            ),
        }
        result = enrich_message(message)
        assert result["appmsg_type"] == 4
        assert result["appmsg_des"] == "视频描述"


class TestEnrichMessagesBatch:
    """enrich_messages_batch 函数测试"""

    def test_batch_enrich(self) -> None:
        """批量增强消息"""
        messages = [
            {"msg_type": 1, "content": "普通消息"},
            {
                "msg_type": 49,
                "content": '<msg><emoji md5="abc" /></msg>',
            },
            {
                "msg_type": 49,
                "content": (
                    "<msg><appmsg><type>57</type><title>回复</title>"
                    "<refermsg><svrid>123</svrid><type>1</type>"
                    "<content>原消息</content><displayname>Alice</displayname>"
                    "<createtime>1769175533</createtime></refermsg>"
                    "</appmsg></msg>"
                ),
            },
        ]
        results = enrich_messages_batch(messages)

        assert len(results) == 3
        assert "_should_filter" not in results[0]
        assert results[1]["_should_filter"] is True
        assert results[2]["appmsg_type"] == 57
