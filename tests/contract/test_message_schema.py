"""MessageContent Schema 契约测试

验证 MessageContent Pydantic 模型的 API 契约稳定性。
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.message_schema import ContactSync, MessageContent


class TestMessageContentContract:
    """MessageContent 模型契约测试"""

    def test_required_fields(self):
        """测试必填字段契约"""
        # 缺少必填字段应该抛出 ValidationError
        with pytest.raises(ValidationError) as exc_info:
            MessageContent()

        # 验证错误信息包含所有必填字段
        error_dict = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in error_dict if err["type"] == "missing"}

        expected_required = {
            "msg_id",
            "from_username",
            "to_username",
            "msg_type",
            "create_time",
            "is_chatroom_msg",
            "source",
            "guid",
            "notify_type",
        }

        assert expected_required.issubset(missing_fields), (
            f"必填字段契约变更: 期望 {expected_required}, 实际缺失 {missing_fields}"
        )

    def test_minimal_valid_message(self):
        """测试最小有效消息契约"""
        # 最小有效消息应该成功创建
        msg = MessageContent(
            msg_id="test_123",
            from_username="wxid_sender",
            to_username="wxid_receiver",
            msg_type=1,
            create_time=1737590400,
            is_chatroom_msg=0,
            source="0",
            guid="test-guid-123",
            notify_type=100,
        )

        # 验证字段值
        assert msg.msg_id == "test_123"
        assert msg.from_username == "wxid_sender"
        assert msg.to_username == "wxid_receiver"
        assert msg.msg_type == 1
        assert msg.create_time == 1737590400
        assert msg.is_chatroom_msg == 0
        assert msg.source == "0"
        assert msg.guid == "test-guid-123"
        assert msg.notify_type == 100

        # 验证默认值
        assert msg.chatroom == ""
        assert msg.chatroom_sender == ""
        assert msg.content == ""
        assert msg.desc == ""
        assert isinstance(msg.ingestion_time, datetime)

    def test_source_field_normalization(self):
        """测试 source 字段类型归一化契约"""
        # source 为整数时应自动转换为字符串
        msg_int_source = MessageContent(
            msg_id="test_123",
            from_username="wxid_sender",
            to_username="wxid_receiver",
            msg_type=1,
            create_time=1737590400,
            is_chatroom_msg=0,
            source=123,  # 整数
            guid="test-guid-123",
            notify_type=100,
        )
        assert msg_int_source.source == "123"
        assert isinstance(msg_int_source.source, str)

        # source 为字符串时保持不变
        msg_str_source = MessageContent(
            msg_id="test_123",
            from_username="wxid_sender",
            to_username="wxid_receiver",
            msg_type=1,
            create_time=1737590400,
            is_chatroom_msg=0,
            source="abc",  # 字符串
            guid="test-guid-123",
            notify_type=100,
        )
        assert msg_str_source.source == "abc"

        # source 为 None 时转换为空字符串
        msg_none_source = MessageContent(
            msg_id="test_123",
            from_username="wxid_sender",
            to_username="wxid_receiver",
            msg_type=1,
            create_time=1737590400,
            is_chatroom_msg=0,
            source=None,  # None
            guid="test-guid-123",
            notify_type=100,
        )
        assert msg_none_source.source == ""

    def test_field_validation_constraints(self):
        """测试字段验证约束契约"""
        # msg_type 必须 >= 0
        with pytest.raises(ValidationError):
            MessageContent(
                msg_id="test_123",
                from_username="wxid_sender",
                to_username="wxid_receiver",
                msg_type=-1,  # 无效
                create_time=1737590400,
                is_chatroom_msg=0,
                source="0",
                guid="test-guid-123",
                notify_type=100,
            )

        # create_time 必须 > 0
        with pytest.raises(ValidationError):
            MessageContent(
                msg_id="test_123",
                from_username="wxid_sender",
                to_username="wxid_receiver",
                msg_type=1,
                create_time=0,  # 无效
                is_chatroom_msg=0,
                source="0",
                guid="test-guid-123",
                notify_type=100,
            )

        # is_chatroom_msg 必须是 0 或 1
        with pytest.raises(ValidationError):
            MessageContent(
                msg_id="test_123",
                from_username="wxid_sender",
                to_username="wxid_receiver",
                msg_type=1,
                create_time=1737590400,
                is_chatroom_msg=2,  # 无效
                source="0",
                guid="test-guid-123",
                notify_type=100,
            )

        # notify_type 必须 >= 0
        with pytest.raises(ValidationError):
            MessageContent(
                msg_id="test_123",
                from_username="wxid_sender",
                to_username="wxid_receiver",
                msg_type=1,
                create_time=1737590400,
                is_chatroom_msg=0,
                source="0",
                guid="test-guid-123",
                notify_type=-1,  # 无效
            )

    def test_model_dict_serialization(self):
        """测试模型字典序列化契约"""
        msg = MessageContent(
            msg_id="test_123",
            from_username="wxid_sender",
            to_username="wxid_receiver",
            msg_type=1,
            create_time=1737590400,
            is_chatroom_msg=0,
            source="0",
            guid="test-guid-123",
            notify_type=100,
        )

        # 转换为字典
        msg_dict = msg.model_dump()

        # 验证所有字段都存在
        expected_fields = {
            "msg_id",
            "from_username",
            "to_username",
            "chatroom",
            "chatroom_sender",
            "msg_type",
            "create_time",
            "is_chatroom_msg",
            "content",
            "desc",
            "source",
            "guid",
            "notify_type",
            "ingestion_time",
        }
        assert set(msg_dict.keys()) == expected_fields

        # 验证可以从字典重建
        msg_rebuilt = MessageContent(**msg_dict)
        assert msg_rebuilt.msg_id == msg.msg_id
        assert msg_rebuilt.from_username == msg.from_username


class TestContactSyncContract:
    """ContactSync 模型契约测试"""

    def test_required_fields(self):
        """测试必填字段契约"""
        # 缺少必填字段应该抛出 ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ContactSync()

        # 验证错误信息包含必填字段
        error_dict = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in error_dict if err["type"] == "missing"}

        expected_required = {"username", "guid", "notify_type"}

        assert expected_required.issubset(missing_fields), (
            f"必填字段契约变更: 期望 {expected_required}, 实际缺失 {missing_fields}"
        )

    def test_minimal_valid_contact(self):
        """测试最小有效联系人契约"""
        contact = ContactSync(username="wxid_test", guid="test-guid-456", notify_type=101)

        # 验证必填字段
        assert contact.username == "wxid_test"
        assert contact.guid == "test-guid-456"
        assert contact.notify_type == 101

        # 验证默认值
        assert contact.alias == ""
        assert contact.encryptUserName == ""
        assert contact.contactType == 0
        assert contact.deleteFlag == 0
        assert contact.verifyFlag == 0
        assert contact.sex == 0
        assert contact.country == ""
        assert contact.province == ""
        assert contact.city == ""
        assert contact.mobile == ""
        assert contact.nickName == "{}"
        assert contact.remark == "{}"
        assert contact.snsUserInfo == "{}"
        assert contact.customInfo == "{}"
        assert isinstance(contact.ingestion_time, datetime)

    def test_field_validation_constraints(self):
        """测试字段验证约束契约"""
        # deleteFlag 必须是 0 或 1
        with pytest.raises(ValidationError):
            ContactSync(
                username="wxid_test",
                guid="test-guid-456",
                notify_type=101,
                deleteFlag=2,  # 无效
            )

        # sex 必须是 0-2
        with pytest.raises(ValidationError):
            ContactSync(
                username="wxid_test",
                guid="test-guid-456",
                notify_type=101,
                sex=3,  # 无效
            )

        # contactType 必须 >= 0
        with pytest.raises(ValidationError):
            ContactSync(
                username="wxid_test",
                guid="test-guid-456",
                notify_type=101,
                contactType=-1,  # 无效
            )

    def test_model_dict_serialization(self):
        """测试模型字典序列化契约"""
        contact = ContactSync(
            username="wxid_test", guid="test-guid-456", notify_type=101, alias="TestUser", sex=1
        )

        # 转换为字典
        contact_dict = contact.model_dump()

        # 验证所有字段都存在
        expected_fields = {
            "username",
            "alias",
            "encryptUserName",
            "contactType",
            "deleteFlag",
            "verifyFlag",
            "sex",
            "country",
            "province",
            "city",
            "mobile",
            "nickName",
            "remark",
            "snsUserInfo",
            "customInfo",
            "guid",
            "notify_type",
            "ingestion_time",
        }
        assert set(contact_dict.keys()) == expected_fields

        # 验证可以从字典重建
        contact_rebuilt = ContactSync(**contact_dict)
        assert contact_rebuilt.username == contact.username
        assert contact_rebuilt.alias == contact.alias
