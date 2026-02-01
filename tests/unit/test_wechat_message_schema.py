"""Tests for src/models/wechat_message_schema.py

TDD: 测试微信消息 Schema 的 Pydantic 模型验证
"""

import pytest
from pydantic import ValidationError

from src.models.wechat_message_schema import (
    AdditionalContactList,
    ContactDeleteData,
    ContactDetailData,
    ContactUpdateData,
    CustomInfoDetail,
    CustomizedInfo,
    ImageBuffer,
    LinkedinContactItem,
    MessageData,
    MessageType,
    NewChatroomData,
    NotifyType,
    PhoneNumListInfo,
    RingBackSetting,
    SnsUserInfo,
    StringWrapper,
    WechatMessage,
)


class TestNotifyTypeEnum:
    """测试通知类型枚举"""

    def test_message_notify_type(self):
        """测试消息通知类型"""
        assert NotifyType.MESSAGE == 1010

    def test_contact_update_notify_type(self):
        """测试联系人更新类型"""
        assert NotifyType.CONTACT_UPDATE == 1200

    def test_contact_delete_notify_type(self):
        """测试联系人删除类型"""
        assert NotifyType.CONTACT_DELETE == 1201

    def test_contact_detail_notify_type(self):
        """测试联系人详情类型"""
        assert NotifyType.CONTACT_DETAIL == 1202

    def test_unknown_notify_type(self):
        """测试未知类型"""
        assert NotifyType.UNKNOWN_1003 == 1003


class TestMessageTypeEnum:
    """测试消息类型枚举"""

    def test_text_message_type(self):
        """测试文本消息类型"""
        assert MessageType.TEXT == 1

    def test_image_message_type(self):
        """测试图片消息类型"""
        assert MessageType.IMAGE == 3

    def test_voice_message_type(self):
        """测试语音消息类型"""
        assert MessageType.VOICE == 34

    def test_video_message_type(self):
        """测试视频消息类型"""
        assert MessageType.VIDEO == 43

    def test_emotion_message_type(self):
        """测试表情消息类型"""
        assert MessageType.EMOTION == 47

    def test_app_message_type(self):
        """测试应用消息类型"""
        assert MessageType.APP_MESSAGE == 49

    def test_system_message_type(self):
        """测试系统消息类型"""
        assert MessageType.SYSTEM == 10000

    def test_recall_message_type(self):
        """测试撤回消息类型"""
        assert MessageType.RECALL == 10002


class TestMessageData:
    """测试消息数据模型"""

    def test_valid_message_data(self):
        """测试有效的消息数据"""
        data = MessageData(
            from_username="wxid_abc123",
            to_username="njin_cool",
            create_time=1762232533,
            msg_id="9019246177609020522",
            is_chatroom_msg=0,
            content="Hello, world!",
        )

        assert data.from_username == "wxid_abc123"
        assert data.to_username == "njin_cool"
        assert data.content == "Hello, world!"

    def test_message_data_with_optional_fields(self):
        """测试带可选字段的消息数据"""
        data = MessageData(
            from_username="wxid_abc123",
            to_username="njin_cool",
            chatroom_sender="wxid_sender",
            create_time=1762232533,
            desc="描述",
            msg_id="9019246177609020522",
            msg_type=1,
            is_chatroom_msg=1,
            chatroom="12345@chatroom",
            source="<msgsource>...</msgsource>",
            content="群消息",
        )

        assert data.chatroom_sender == "wxid_sender"
        assert data.msg_type == 1
        assert data.chatroom == "12345@chatroom"

    def test_message_data_missing_required_field(self):
        """测试缺少必填字段"""
        with pytest.raises(ValidationError):
            MessageData(
                from_username="wxid_abc123",
                # missing to_username
                create_time=1762232533,
                msg_id="9019246177609020522",
                is_chatroom_msg=0,
                content="Hello",
            )

    def test_message_data_default_values(self):
        """测试默认值"""
        data = MessageData(
            from_username="wxid_abc123",
            to_username="njin_cool",
            create_time=1762232533,
            msg_id="9019246177609020522",
            is_chatroom_msg=0,
            content="Hello",
        )

        assert data.chatroom_sender == ""
        assert data.desc == ""
        assert data.chatroom == ""
        assert data.source == ""
        assert data.msg_type is None


class TestStringWrapper:
    """测试字符串包装器"""

    def test_string_wrapper(self):
        """测试字符串包装器"""
        wrapper = StringWrapper(string="test_value")
        assert wrapper.string == "test_value"


class TestImageBuffer:
    """测试图片缓冲区"""

    def test_image_buffer_default(self):
        """测试图片缓冲区默认值"""
        buffer = ImageBuffer()
        assert buffer.iLen == 0

    def test_image_buffer_with_value(self):
        """测试图片缓冲区带值"""
        buffer = ImageBuffer(iLen=1024)
        assert buffer.iLen == 1024


class TestSnsUserInfo:
    """测试朋友圈用户信息"""

    def test_sns_user_info_defaults(self):
        """测试朋友圈用户信息默认值"""
        info = SnsUserInfo()
        assert info.snsFlag == 0
        assert info.snsBgobjectId == "0"
        assert info.snsFlagEx == 0
        assert info.snsPrivacyRecent == 0


class TestCustomizedInfo:
    """测试自定义信息"""

    def test_customized_info_default(self):
        """测试自定义信息默认值"""
        info = CustomizedInfo()
        assert info.brandFlag == 0


class TestLinkedinContactItem:
    """测试 LinkedIn 联系信息"""

    def test_linkedin_contact_item(self):
        """测试 LinkedIn 联系信息"""
        item = LinkedinContactItem()
        assert item is not None


class TestAdditionalContactList:
    """测试额外联系信息列表"""

    def test_additional_contact_list_default(self):
        """测试额外联系信息列表默认值"""
        contact_list = AdditionalContactList()
        assert isinstance(contact_list.linkedinContactItem, LinkedinContactItem)


class TestNewChatroomData:
    """测试新建群聊数据"""

    def test_new_chatroom_data_defaults(self):
        """测试新建群聊数据默认值"""
        data = NewChatroomData()
        assert data.memberCount == 0
        assert data.infoMask == 0
        assert data.chatRoomUserName == {}
        assert data.watchMemberCount == 0


class TestPhoneNumListInfo:
    """测试手机号列表信息"""

    def test_phone_num_list_info_default(self):
        """测试手机号列表信息默认值"""
        info = PhoneNumListInfo()
        assert info.count == 0


class TestRingBackSetting:
    """测试回铃音设置"""

    def test_ring_back_setting_defaults(self):
        """测试回铃音设置默认值"""
        setting = RingBackSetting()
        assert setting.finderObjectId == "0"
        assert setting.startTs == 0
        assert setting.endTs == 0


class TestContactUpdateData:
    """测试联系人更新数据"""

    def test_contact_update_data_minimal(self):
        """测试最小联系人更新数据"""
        data = ContactUpdateData()
        assert data.userName is None
        assert data.nickName is None

    def test_contact_update_data_with_username(self):
        """测试带用户名的联系人更新数据"""
        data = ContactUpdateData(
            userName=StringWrapper(string="53538129723@chatroom"),
            nickName=StringWrapper(string="安得同行"),
            sex=0,
        )

        assert data.userName.string == "53538129723@chatroom"
        assert data.nickName.string == "安得同行"
        assert data.sex == 0

    def test_contact_update_data_with_all_fields(self):
        """测试带所有字段的联系人更新数据"""
        data = ContactUpdateData(
            userName=StringWrapper(string="wxid_test"),
            nickName=StringWrapper(string="测试用户"),
            sex=1,
            smallHeadImgUrl="https://wx.qlogo.cn/mmcrhead/test",
            chatroomVersion=10616,
            chatroomMaxCount=500,
            contactType=1,
            verifyFlag=0,
            city="北京",
            country="中国",
            province="北京",
        )

        assert data.smallHeadImgUrl == "https://wx.qlogo.cn/mmcrhead/test"
        assert data.chatroomMaxCount == 500
        assert data.city == "北京"


class TestContactDeleteData:
    """测试联系人删除数据"""

    def test_contact_delete_data(self):
        """测试联系人删除数据"""
        data = ContactDeleteData(userName=StringWrapper(string="wxid_deleted"))

        assert data.userName.string == "wxid_deleted"
        assert data.deleteContactScene == 0

    def test_contact_delete_data_with_scene(self):
        """测试带场景的联系人删除数据"""
        data = ContactDeleteData(
            userName=StringWrapper(string="wxid_deleted"),
            deleteContactScene=1,
        )

        assert data.deleteContactScene == 1


class TestCustomInfoDetail:
    """测试自定义信息详情"""

    def test_custom_info_detail_defaults(self):
        """测试自定义信息详情默认值"""
        detail = CustomInfoDetail()
        assert detail.detailVisible == 1
        assert detail.detail == ""

    def test_custom_info_detail_with_values(self):
        """测试带值的自定义信息详情"""
        detail = CustomInfoDetail(detailVisible=0, detail='{"key": "value"}')
        assert detail.detailVisible == 0
        assert detail.detail == '{"key": "value"}'


class TestContactDetailData:
    """测试联系人详情数据"""

    def test_contact_detail_data_minimal(self):
        """测试最小联系人详情数据"""
        data = ContactDetailData(
            tpUsername="wxid_test",
            nickname="测试用户",
            type=1,
            source=0,
        )

        assert data.tpUsername == "wxid_test"
        assert data.nickname == "测试用户"
        assert data.type == 1
        assert data.source == 0

    def test_contact_detail_data_with_optional_fields(self):
        """测试带可选字段的联系人详情数据"""
        data = ContactDetailData(
            tpUsername="wxid_test",
            nickname="测试用户",
            type=1,
            remark="备注名",
            bigHeadimg="https://example.com/big.jpg",
            smallHeadimg="https://example.com/small.jpg",
            source=0,
            nicknamePyinit="CSYH",
            nicknameQuanpin="ceshiyonghu",
            sex=1,
        )

        assert data.remark == "备注名"
        assert data.bigHeadimg == "https://example.com/big.jpg"
        assert data.sex == 1


class TestWechatMessage:
    """测试微信消息顶层结构"""

    def test_wechat_message_with_message_data(self):
        """测试带消息数据的微信消息"""
        message = WechatMessage(
            guid="7092457f-325f-3b3a-bf8e-a30b4dcaf74b",
            notify_type=1010,
            data=MessageData(
                from_username="wxid_abc123",
                to_username="njin_cool",
                create_time=1762232533,
                msg_id="9019246177609020522",
                is_chatroom_msg=0,
                content="Hello!",
            ),
        )

        assert message.guid == "7092457f-325f-3b3a-bf8e-a30b4dcaf74b"
        assert message.notify_type == 1010
        assert isinstance(message.data, MessageData)

    def test_wechat_message_with_contact_update(self):
        """测试带联系人更新的微信消息"""
        message = WechatMessage(
            guid="test-guid",
            notify_type=1200,
            data=ContactUpdateData(
                userName=StringWrapper(string="wxid_test"),
                nickName=StringWrapper(string="测试"),
            ),
        )

        assert message.notify_type == 1200
        assert isinstance(message.data, ContactUpdateData)

    def test_wechat_message_with_contact_delete(self):
        """测试带联系人删除的微信消息"""
        message = WechatMessage(
            guid="test-guid",
            notify_type=1201,
            data=ContactDeleteData(userName=StringWrapper(string="wxid_deleted")),
        )

        assert message.notify_type == 1201
        assert isinstance(message.data, ContactDeleteData)

    def test_wechat_message_with_contact_detail(self):
        """测试带联系人详情的微信消息"""
        message = WechatMessage(
            guid="test-guid",
            notify_type=1202,
            data=ContactDetailData(
                tpUsername="wxid_test",
                nickname="测试",
                type=1,
                source=0,
            ),
        )

        assert message.notify_type == 1202
        assert isinstance(message.data, ContactDetailData)

    def test_wechat_message_missing_guid(self):
        """测试缺少 guid 的微信消息"""
        with pytest.raises(ValidationError):
            WechatMessage(
                notify_type=1010,
                data=MessageData(
                    from_username="wxid_abc123",
                    to_username="njin_cool",
                    create_time=1762232533,
                    msg_id="9019246177609020522",
                    is_chatroom_msg=0,
                    content="Hello!",
                ),
            )

    def test_wechat_message_serialization(self):
        """测试微信消息序列化"""
        message = WechatMessage(
            guid="test-guid",
            notify_type=1010,
            data=MessageData(
                from_username="wxid_abc123",
                to_username="njin_cool",
                create_time=1762232533,
                msg_id="9019246177609020522",
                is_chatroom_msg=0,
                content="Hello!",
            ),
        )

        data_dict = message.model_dump()
        assert data_dict["guid"] == "test-guid"
        assert data_dict["notify_type"] == 1010
        assert data_dict["data"]["from_username"] == "wxid_abc123"
