"""
微信消息 Schema 定义

基于 52,554 条真实消息数据分析生成的完整 Schema。
支持所有已知的消息类型和通知类型。
"""

from enum import IntEnum

from pydantic import BaseModel, Field


class NotifyType(IntEnum):
    """通知类型枚举"""

    MESSAGE = 1010  # 消息通知 (51,863条)
    CONTACT_UPDATE = 1200  # 联系人更新 (669条)
    CONTACT_DELETE = 1201  # 联系人删除 (3条)
    CONTACT_DETAIL = 1202  # 联系人详情 (18条)
    UNKNOWN_1003 = 1003  # 未知类型 (1条)


class MessageType(IntEnum):
    """消息类型枚举"""

    TEXT = 1  # 文本消息 (28,137条)
    IMAGE = 3  # 图片消息 (3,205条)
    VOICE = 34  # 语音消息 (22条)
    FRIEND_VERIFY = 37  # 好友验证 (1条)
    CARD = 42  # 名片消息 (3条)
    VIDEO = 43  # 视频消息 (185条)
    EMOTION = 47  # 表情消息 (2,014条)
    LOCATION = 48  # 位置消息 (4条)
    APP_MESSAGE = 49  # 应用消息/链接 (10,478条)
    VOIP = 50  # 语音/视频通话 (2条)
    MICRO_VIDEO = 51  # 微视频/视频号 (6,713条)
    SYSTEM = 10000  # 系统消息 (92条)
    RECALL = 10002  # 撤回消息 (1,007条)


# ============================================================================
# notify_type = 1010: 消息通知
# ============================================================================


class MessageData(BaseModel):
    """消息数据基础模型 (notify_type=1010)"""

    from_username: str = Field(..., description="发送者用户名")
    to_username: str = Field(..., description="接收者用户名")
    chatroom_sender: str = Field(default="", description="群聊发送者(仅群聊消息)")
    create_time: int = Field(..., description="消息创建时间戳")
    desc: str = Field(default="", description="消息描述")
    msg_id: str = Field(..., description="消息ID")
    msg_type: int | None = Field(None, description="消息类型")
    is_chatroom_msg: int = Field(..., description="是否群聊消息 (0=否, 1=是)")
    chatroom: str = Field(default="", description="群聊ID")
    source: str = Field(default="", description="消息来源XML")
    content: str = Field(..., description="消息内容")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "from_username": "wxid_abc123",
                    "to_username": "njin_cool",
                    "chatroom_sender": "",
                    "create_time": 1762232533,
                    "desc": "",
                    "msg_id": "9019246177609020522",
                    "msg_type": 1,
                    "is_chatroom_msg": 0,
                    "chatroom": "",
                    "source": "<msgsource>...</msgsource>",
                    "content": "Hello, world!",
                }
            ]
        }


# ============================================================================
# notify_type = 1200: 联系人更新
# ============================================================================


class StringWrapper(BaseModel):
    """字符串包装器"""

    string: str


class ImageBuffer(BaseModel):
    """图片缓冲区"""

    iLen: int = Field(default=0, description="缓冲区长度")


class SnsUserInfo(BaseModel):
    """朋友圈用户信息"""

    snsFlag: int = Field(default=0)
    snsBgobjectId: str = Field(default="0")
    snsFlagEx: int = Field(default=0)
    snsPrivacyRecent: int = Field(default=0)


class CustomizedInfo(BaseModel):
    """自定义信息"""

    brandFlag: int = Field(default=0)


class LinkedinContactItem(BaseModel):
    """LinkedIn 联系信息"""

    pass


class AdditionalContactList(BaseModel):
    """额外联系信息列表"""

    linkedinContactItem: LinkedinContactItem = Field(default_factory=LinkedinContactItem)


class NewChatroomData(BaseModel):
    """新建群聊数据"""

    memberCount: int = Field(default=0)
    infoMask: int = Field(default=0)
    chatRoomUserName: dict = Field(default_factory=dict)
    watchMemberCount: int = Field(default=0)


class PhoneNumListInfo(BaseModel):
    """手机号列表信息"""

    count: int = Field(default=0)


class RingBackSetting(BaseModel):
    """回铃音设置"""

    finderObjectId: str = Field(default="0")
    startTs: int = Field(default=0)
    endTs: int = Field(default=0)


class ContactUpdateData(BaseModel):
    """联系人更新数据 (notify_type=1200)"""

    userName: StringWrapper | None = Field(None, description="用户名")
    nickName: StringWrapper | None = Field(None, description="昵称")
    pyinitial: StringWrapper | None = Field(None, description="拼音首字母")
    quanPin: StringWrapper | None = Field(None, description="全拼")
    sex: int | None = Field(None, description="性别 (0=未知, 1=男, 2=女)")
    imgBuf: ImageBuffer | None = Field(None, description="头像缓冲区")
    bitMask: int | None = Field(None, description="位掩码")
    bitVal: int | None = Field(None, description="位值")
    imgFlag: int | None = Field(None, description="头像标志")
    remark: dict | None = Field(None, description="备注")
    remarkPyinitial: dict | None = Field(None, description="备注拼音首字母")
    remarkQuanPin: dict | None = Field(None, description="备注全拼")
    contactType: int | None = Field(None, description="联系人类型")
    roomInfoCount: int | None = Field(None, description="群聊信息数量")
    domainList: dict | None = Field(None, description="域名列表")
    chatRoomNotify: int | None = Field(None, description="群聊通知")
    addContactScene: int | None = Field(None, description="添加联系人场景")
    personalCard: int | None = Field(None, description="个人名片")
    hasWeiXinHdHeadImg: int | None = Field(None, description="是否有高清头像")
    verifyFlag: int | None = Field(None, description="验证标志")
    level: int | None = Field(None, description="等级")
    source: int | None = Field(None, description="来源")
    weiboFlag: int | None = Field(None, description="微博标志")
    albumStyle: int | None = Field(None, description="相册样式")
    albumFlag: int | None = Field(None, description="相册标志")
    snsUserInfo: SnsUserInfo | None = Field(None, description="朋友圈用户信息")
    smallHeadImgUrl: str | None = Field(None, description="小头像URL")
    customizedInfo: CustomizedInfo | None = Field(None, description="自定义信息")
    additionalContactList: AdditionalContactList | None = Field(None, description="额外联系信息")
    chatroomVersion: int | None = Field(None, description="群聊版本")
    chatroomMaxCount: int | None = Field(None, description="群聊最大人数")
    chatroomAccessType: int | None = Field(None, description="群聊访问类型")
    newChatroomData: NewChatroomData | None = Field(None, description="新建群聊数据")
    deleteFlag: int | None = Field(None, description="删除标志")
    phoneNumListInfo: PhoneNumListInfo | None = Field(None, description="手机号列表信息")
    chatroomInfoVersion: int | None = Field(None, description="群聊信息版本")
    deleteContactScene: int | None = Field(None, description="删除联系人场景")
    chatroomStatus: int | None = Field(None, description="群聊状态")
    extFlag: int | None = Field(None, description="扩展标志")
    chatRoomBusinessType: str | None = Field(None, description="群聊业务类型")
    textStatusFlag: int | None = Field(None, description="文本状态标志")
    ringBackSetting: RingBackSetting | None = Field(None, description="回铃音设置")
    bitMask2: str | None = Field(None, description="位掩码2")
    bitValue2: str | None = Field(None, description="位值2")
    contactExtraInfoBuf: ImageBuffer | None = Field(None, description="联系人额外信息缓冲区")
    isInChatRoom: int | None = Field(None, description="是否在群聊中")
    eraseChatRoomMemberData: int | None = Field(None, description="擦除群聊成员数据")

    # 其他可能的字段
    alias: str | None = Field(None, description="别名")
    albumBgimgId: str | None = Field(None, description="相册背景图ID")
    bigHeadImgUrl: str | None = Field(None, description="大头像URL")
    city: str | None = Field(None, description="城市")
    country: str | None = Field(None, description="国家")
    encryptUserName: str | None = Field(None, description="加密用户名")
    flag: int | str | None = Field(None, description="标志")
    mobile: str | None = Field(None, description="手机号")
    province: str | None = Field(None, description="省份")
    signature: str | None = Field(None, description="个性签名")
    verifyInfo: str | None = Field(None, description="验证信息")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "userName": {"string": "53538129723@chatroom"},
                    "nickName": {"string": "安得同行"},
                    "sex": 0,
                    "smallHeadImgUrl": "https://wx.qlogo.cn/mmcrhead/...",
                    "chatroomVersion": 10616,
                    "chatroomMaxCount": 500,
                }
            ]
        }


# ============================================================================
# notify_type = 1201: 联系人删除
# ============================================================================


class ContactDeleteData(BaseModel):
    """联系人删除数据 (notify_type=1201)"""

    userName: StringWrapper = Field(..., description="用户名")
    deleteContactScene: int = Field(default=0, description="删除联系人场景")


# ============================================================================
# notify_type = 1202: 联系人详情
# ============================================================================


class CustomInfoDetail(BaseModel):
    """自定义信息详情"""

    detailVisible: int = Field(default=1)
    detail: str = Field(default="", description="详情JSON字符串")


class ContactDetailData(BaseModel):
    """联系人详情数据 (notify_type=1202)"""

    tpUsername: str = Field(..., description="第三方用户名")
    nickname: str = Field(..., description="昵称")
    type: int = Field(..., description="类型")
    remark: str = Field(default="", description="备注")
    bigHeadimg: str = Field(default="", description="大头像")
    smallHeadimg: str = Field(default="", description="小头像")
    source: int = Field(..., description="来源")
    nicknamePyinit: str = Field(default="", description="昵称拼音首字母")
    nicknameQuanpin: str = Field(default="", description="昵称全拼")
    remarkPyinit: str = Field(default="", description="备注拼音首字母")
    remarkQuanpin: str = Field(default="", description="备注全拼")
    customInfo: CustomInfoDetail | None = Field(None, description="自定义信息")
    appId: str | None = Field(None, description="应用ID")
    sex: int | None = Field(None, description="性别")
    descWordingId: str | None = Field(None, description="描述文案ID")
    finderUsername: str | None = Field(None, description="视频号用户名")
    flag: str | None = Field(None, description="标志")


# ============================================================================
# 顶层消息结构
# ============================================================================


class WechatMessage(BaseModel):
    """微信消息顶层结构"""

    guid: str = Field(..., description="全局唯一标识符")
    notify_type: int = Field(..., description="通知类型")
    data: MessageData | ContactUpdateData | ContactDeleteData | ContactDetailData = Field(
        ..., description="消息数据"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "guid": "7092457f-325f-3b3a-bf8e-a30b4dcaf74b",
                    "notify_type": 1010,
                    "data": {
                        "from_username": "wxid_abc123",
                        "to_username": "njin_cool",
                        "msg_type": 1,
                        "content": "Hello!",
                    },
                }
            ]
        }


# ============================================================================
# 统计信息
# ============================================================================

MESSAGE_TYPE_STATS = {
    "统计来源": "52,554条真实消息",
    "notify_type分布": {
        1010: {"name": "消息通知", "count": 51863},
        1200: {"name": "联系人更新", "count": 669},
        1202: {"name": "联系人详情", "count": 18},
        1201: {"name": "联系人删除", "count": 3},
        1003: {"name": "未知类型", "count": 1},
    },
    "msg_type分布": {
        1: {"name": "文本消息", "count": 28137},
        49: {"name": "应用消息/链接", "count": 10478},
        51: {"name": "微视频/视频号", "count": 6713},
        3: {"name": "图片消息", "count": 3205},
        47: {"name": "表情消息", "count": 2014},
        10002: {"name": "撤回消息", "count": 1007},
        None: {"name": "空类型", "count": 691},
        43: {"name": "视频消息", "count": 185},
        10000: {"name": "系统消息", "count": 92},
        34: {"name": "语音消息", "count": 22},
        48: {"name": "位置消息", "count": 4},
        42: {"name": "名片消息", "count": 3},
        50: {"name": "语音/视频通话", "count": 2},
        37: {"name": "好友验证", "count": 1},
    },
}
