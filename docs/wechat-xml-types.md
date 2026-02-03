# WeChat XML 类型清单（样例来自 2026-02-02）

本文件记录在 `data/vectors.duckdb` 的 `message_embeddings.content` 中出现的主要 XML 结构类型，并给出样例（已截断）。

## 消息处理策略

在 `analyze-chatrooms` 命令的消息预处理阶段，XML 消息会经过以下处理：

### 过滤的消息类型

以下消息类型会被标记为 `_should_filter=True`，在格式化阶段跳过：

| 类型 | 识别方式 | 过滤原因 |
|------|----------|----------|
| `appmsg:type=3` | `<appmsg><type>3</type>` | 音乐分享，无文本价值 |
| `appmsg:type=47` | `<appmsg><type>47</type>` | 系统提示 |
| `appmsg:type=51` | `<appmsg><type>51</type>` | 系统提示 |
| `appmsg:type=124` | `<appmsg><type>124</type>` | 版本过低提示 |
| `appmsg:type=1+refermsg` | `<appmsg><type>1</type><refermsg>` | 轻量引用/表态式回复（如"🫡"） |
| `emoji` | `<msg><emoji .../>` | 表情包，无文本内容 |
| `voicemsg` | `<msg><voicemsg .../>` | 语音消息，无文本内容 |
| `op:lastMessage` | `<op><name>lastMessage</name>` | 系统操作/游标 |
| `sysmsg` | `<sysmsg type="...">` | 系统消息（撤回等） |

### 特殊处理的消息类型

| 类型 | 处理方式 | 格式化输出 |
|------|----------|------------|
| `appmsg:type=57` | 提取 `refermsg` 引用消息 | `[引用 @发送者: 内容] 回复内容` |
| `appmsg:type=49` | 提取 `refermsg` 引用消息 | `[引用 @发送者: 内容] 回复内容` |
| `appmsg:type=5` | 提取 `title` 和 `des` | `[分享] 标题` |
| `appmsg:type=4` | 提取 `title` 和 `des` | `[分享] 标题` |

### 相关代码

- `src/diting/lib/xml_parser.py` - XML 解析和类型识别
- `src/diting/services/llm/message_enricher.py` - 消息增强（添加过滤标记）
- `src/diting/services/llm/message_formatter.py` - 消息格式化（执行过滤）

---

## appmsg（分享类消息）

### appmsg:type=57 + refermsg（引用/回复）
用于“引用某条消息”的卡片式回复，`refermsg` 内含原消息内容。

```xml
<?xml version="1.0"?> <msg> <appmsg appid="" sdkver="0">
  <title>感觉年前够呛</title>
  <type>57</type>
  <refermsg>
    <displayname>幸运的掺和</displayname>
    <content>打伊朗 黄金就上来了</content>
  </refermsg>
</appmsg> ...
```

### appmsg:type=5（链接/红包/文章分享）
常见于公众号文章、红包/活动卡片等。

```xml
<?xml version="1.0"?> <msg> <appmsg>
  <title>Eva给你发了一个现金红包！</title>
  <des>元宝派红包，新春领不停</des>
  <type>5</type>
  <url>https://...</url>
</appmsg> ...
```

### appmsg:type=3（音乐分享）
音乐卡片，含标题与歌手信息。

```xml
<msg> <appmsg appid="wx5aa333606550dfd5" sdkver="0">
  <title>大城小爱</title>
  <des>王力宏</des>
  <type>3</type>
  <url>https://i.y.qq.com/v8/playsong.html?...</url>
</appmsg> ...
```

### appmsg:type=4（视频/图文分享）
多为短视频/图文链接分享。

```xml
<?xml version="1.0"?> <msg> <appmsg appid="wxd8a2750ce9d46980" sdkver="0">
  <title>坏兔子格莱美奖公开抵制 ICE</title>
  <des>#格莱美奖 ...</des>
  <type>4</type>
  <url>https://www.xiaohongshu.com/discovery/item/...</url>
</appmsg> ...
```

### appmsg:type=124 / 47 / 51（版本过低/系统提示）
典型为系统提示或功能不可用卡片。

```xml
<msg> <appmsg appid="" sdkver="0">
  <title>微信礼物</title>
  <type>124</type>
  <des>当前版本暂不支持查看礼物，请更新微信版本</des>
  <url>https://support.weixin.qq.com/security/...</url>
</appmsg> ...
```

### appmsg:type=1 + refermsg（轻量引用型互动）
多为“表态式”卡片回复（如“🫡”）。

```xml
<?xml version="1.0"?> <msg> <appmsg>
  <title>🫡</title>
  <type>1</type>
  <refermsg>...</refermsg>
</appmsg> ...
```

### appmsg:type=49 + refermsg（引用型转发/卡片）
结构与 type=57 类似，但类型不同。

```xml
<?xml version="1.0"?> <msg> <appmsg>
  <title>政策是这样 一开始肯定是你好我好</title>
  <type>49</type>
  <refermsg>...</refermsg>
</appmsg> ...
```

## emoji（表情包）

```xml
<msg><emoji fromusername="wxid_..." md5="be0b0e..." len="19440" ... /></msg>
```

## img（图片消息）

```xml
<?xml version="1.0"?> <msg>
  <img aeskey="..." cdnthumburl="..." cdnthumbwidth="337" ... />
</msg>
```

## voicemsg（语音消息）

```xml
<msg><voicemsg voicelength="24600" voiceurl="..." ... /></msg>
```

## op:lastMessage（系统操作/游标）

```xml
<msg> <op id='5'>
  <name>lastMessage</name>
  <arg>{"messageSvrId":"...","MsgCreateTime":"..."}</arg>
</op> </msg>
```

## sysmsg（系统消息，如撤回）

```xml
<sysmsg type="revokemsg">
  <revokemsg><session>...</session><replacemsg><![CDATA["某人" 撤回了一条消息]]></replacemsg></revokemsg>
</sysmsg>
```
