"""MessageNormalizer 单元测试"""

from src.services.storage.message_normalizer import (
    MessageNormalizer,
    extract_message_payload,
    prepare_messages,
)


class TestMessageNormalizerExtractPayload:
    """extract_payload 方法测试"""

    def test_extracts_data_field(self):
        """测试提取 data 字段"""
        normalizer = MessageNormalizer()
        message = {
            "guid": "test-guid",
            "notify_type": 1010,
            "data": {
                "msg_id": "msg-001",
                "content": "Hello",
            },
        }
        result = normalizer.extract_payload(message)

        assert result["msg_id"] == "msg-001"
        assert result["content"] == "Hello"
        assert result["guid"] == "test-guid"
        assert result["notify_type"] == 1010

    def test_returns_original_when_msg_id_exists(self):
        """测试当 msg_id 已存在时返回原始消息"""
        normalizer = MessageNormalizer()
        message = {
            "msg_id": "msg-001",
            "content": "Hello",
            "data": {"other": "data"},
        }
        result = normalizer.extract_payload(message)

        assert result == message

    def test_returns_original_when_no_data_field(self):
        """测试无 data 字段时返回原始消息"""
        normalizer = MessageNormalizer()
        message = {"msg_id": "msg-001", "content": "Hello"}
        result = normalizer.extract_payload(message)

        assert result == message

    def test_preserves_existing_guid_in_data(self):
        """测试保留 data 中已有的 guid"""
        normalizer = MessageNormalizer()
        message = {
            "guid": "outer-guid",
            "data": {
                "msg_id": "msg-001",
                "guid": "inner-guid",
            },
        }
        result = normalizer.extract_payload(message)

        assert result["guid"] == "inner-guid"


class TestMessageNormalizerPrepareMessages:
    """prepare_messages 方法测试"""

    def test_filters_messages_without_msg_id(self):
        """测试过滤无 msg_id 的消息"""
        normalizer = MessageNormalizer()
        messages = [
            {"msg_id": "msg-001", "create_time": 1234567890},
            {"create_time": 1234567891},  # 无 msg_id
        ]
        result = normalizer.prepare_messages(messages)

        assert len(result) == 1
        assert result[0]["msg_id"] == "msg-001"

    def test_filters_messages_without_create_time(self):
        """测试过滤无 create_time 的消息"""
        normalizer = MessageNormalizer()
        messages = [
            {"msg_id": "msg-001", "create_time": 1234567890},
            {"msg_id": "msg-002"},  # 无 create_time
            {"msg_id": "msg-003", "create_time": None},
            {"msg_id": "msg-004", "create_time": ""},
        ]
        result = normalizer.prepare_messages(messages)

        assert len(result) == 1
        assert result[0]["msg_id"] == "msg-001"

    def test_fills_default_values(self):
        """测试填充默认值"""
        normalizer = MessageNormalizer()
        messages = [{"msg_id": "msg-001", "create_time": 1234567890}]
        result = normalizer.prepare_messages(messages)

        assert result[0]["from_username"] == ""
        assert result[0]["to_username"] == ""
        assert result[0]["msg_type"] == 0
        assert result[0]["is_chatroom_msg"] == 0
        assert result[0]["source"] == ""
        assert result[0]["guid"] == ""
        assert result[0]["notify_type"] == 0

    def test_adds_ingestion_time(self):
        """测试添加摄入时间"""
        normalizer = MessageNormalizer()
        messages = [{"msg_id": "msg-001", "create_time": 1234567890}]
        result = normalizer.prepare_messages(messages)

        assert "ingestion_time" in result[0]

    def test_preserves_existing_values(self):
        """测试保留已有值"""
        normalizer = MessageNormalizer()
        messages = [
            {
                "msg_id": "msg-001",
                "create_time": 1234567890,
                "from_username": "user1",
                "msg_type": 1,
            }
        ]
        result = normalizer.prepare_messages(messages)

        assert result[0]["from_username"] == "user1"
        assert result[0]["msg_type"] == 1

    def test_returns_empty_for_empty_input(self):
        """测试空输入返回空列表"""
        normalizer = MessageNormalizer()
        result = normalizer.prepare_messages([])

        assert result == []


class TestMessageNormalizerNormalizeCellValue:
    """normalize_cell_value 方法测试"""

    def test_serializes_dict_to_json(self):
        """测试将字典序列化为 JSON"""
        result = MessageNormalizer.normalize_cell_value({"key": "value"})
        assert result == '{"key": "value"}'

    def test_serializes_list_to_json(self):
        """测试将列表序列化为 JSON"""
        result = MessageNormalizer.normalize_cell_value([1, 2, 3])
        assert result == "[1, 2, 3]"

    def test_returns_string_unchanged(self):
        """测试字符串保持不变"""
        result = MessageNormalizer.normalize_cell_value("hello")
        assert result == "hello"

    def test_returns_number_unchanged(self):
        """测试数字保持不变"""
        result = MessageNormalizer.normalize_cell_value(42)
        assert result == 42

    def test_returns_none_unchanged(self):
        """测试 None 保持不变"""
        result = MessageNormalizer.normalize_cell_value(None)
        assert result is None


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_extract_message_payload(self):
        """测试 extract_message_payload 便捷函数"""
        message = {
            "guid": "test-guid",
            "data": {"msg_id": "msg-001"},
        }
        result = extract_message_payload(message)

        assert result["msg_id"] == "msg-001"
        assert result["guid"] == "test-guid"

    def test_prepare_messages(self):
        """测试 prepare_messages 便捷函数"""
        messages = [{"msg_id": "msg-001", "create_time": 1234567890}]
        result = prepare_messages(messages)

        assert len(result) == 1
        assert result[0]["msg_id"] == "msg-001"
