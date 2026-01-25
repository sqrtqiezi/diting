# LLM 分析提示词优化方案：引用消息支持（执行步骤）

## 目标

- 在话题聚合中识别微信引用消息（refermsg）
- 提升归类准确性与可追溯性（message_ids、confidence、notes）
- 不修改 Parquet schema，仅在分析时解析 XML

## 背景与约束

- 引用消息常见结构：`msg_type=49` 且 `<appmsg><type>57</type><refermsg>...</refermsg></appmsg>`
- 解析后的引用信息仅用于提示词上下文增强
- 输出必须保持 JSON，避免多余文本或 Markdown

### 引用消息示例（XML）

```xml
<msg>
    <appmsg appid="" sdkver="0">
        <title>回复内容</title>
        <type>57</type>
        <refermsg>
            <type>1</type>
            <svrid>895098733670197376</svrid>
            <fromusr>38733837988@chatroom</fromusr>
            <chatusr>wxid_5z94exjfp9se12</chatusr>
            <displayname>发送者昵称</displayname>
            <content>被引用的原始消息内容</content>
            <createtime>1769175533</createtime>
        </refermsg>
    </appmsg>
</msg>
```

## 执行步骤

### Step 1: 明确识别规则与字段范围

- 识别条件：`msg_type == 49` 且 `appmsg.type == 57`
- 字段范围（最小可用）：`message_ids`、`confidence`、`notes`
- 约束：不新增 Parquet 列，解析逻辑仅在分析时执行

**产出**：字段清单 + 识别规则说明

### Step 2: 实现 XML 解析器

**目标**：解析 `content` 中的 `<appmsg>` 与 `<refermsg>`，产出结构化字段

**新增文件**：`src/lib/xml_parser.py`

```python
from dataclasses import dataclass
from xml.etree import ElementTree as ET

import structlog

logger = structlog.get_logger()


@dataclass
class ReferMsg:
    svrid: str
    type: int
    content: str
    displayname: str
    createtime: int


@dataclass
class AppmsgContent:
    appmsg_type: int
    title: str
    refermsg: ReferMsg | None = None


def parse_appmsg_content(xml_str: str) -> AppmsgContent | None:
    if not xml_str or not xml_str.strip():
        return None
    try:
        root = ET.fromstring(xml_str)
        appmsg = root.find("appmsg")
        if appmsg is None:
            return None
        appmsg_type = int(appmsg.findtext("type", "0"))
        title = appmsg.findtext("title", "") or ""
        refermsg = _extract_refermsg(appmsg)
        return AppmsgContent(appmsg_type=appmsg_type, title=title, refermsg=refermsg)
    except (ET.ParseError, ValueError, TypeError) as exc:
        logger.warning("appmsg_parse_error", error=str(exc))
        return None


def _extract_refermsg(appmsg: ET.Element) -> ReferMsg | None:
    refermsg_elem = appmsg.find("refermsg")
    if refermsg_elem is None:
        return None
    try:
        return ReferMsg(
            svrid=refermsg_elem.findtext("svrid", ""),
            type=int(refermsg_elem.findtext("type", "0")),
            content=refermsg_elem.findtext("content", ""),
            displayname=refermsg_elem.findtext("displayname", ""),
            createtime=int(refermsg_elem.findtext("createtime", "0")),
        )
    except (ValueError, TypeError) as exc:
        logger.warning("refermsg_parse_error", error=str(exc))
        return None
```

**验收**：对合法 XML 能返回结构化字段；异常 XML 返回 None。

### Step 3: 消息增强服务

**目标**：将解析结果写回消息字典，用于提示词

**新增文件**：`src/services/llm/message_enricher.py`

```python
from typing import Any

from src.lib.xml_parser import parse_appmsg_content


def enrich_message(message: dict[str, Any]) -> dict[str, Any]:
    if message.get("msg_type") != 49:
        return message
    parsed = parse_appmsg_content(message.get("content", ""))
    if parsed is None:
        return message
    message["appmsg_type"] = parsed.appmsg_type
    message["appmsg_title"] = parsed.title
    if parsed.appmsg_type == 57 and parsed.refermsg:
        message["refermsg"] = {
            "svrid": parsed.refermsg.svrid,
            "type": parsed.refermsg.type,
            "content": parsed.refermsg.content,
            "displayname": parsed.refermsg.displayname,
            "createtime": parsed.refermsg.createtime,
        }
    return message
```

**验收**：引用消息具备 `refermsg` 字段；非引用消息保持不变。

### Step 4: 提示词模板化与增强版规则

**目标**：形成 v1/v2 模板；v2 强制输出 `message_ids`、`confidence`、`notes`

**新增文件**：`src/services/llm/prompts.py`

```python
SYSTEM_PROMPT_V2 = """你是微信群聊分析助手。请根据聊天记录，按话题聚合并分类。

## 主题线程切分规则
1. 时间邻近性: 相邻消息时间差 < 10分钟视为同一线程
2. 语义相似性: 讨论同一主题或关键词
3. 问答关系: 明确的提问-回答对
4. 引用关系: 通过 [引用] 标记识别（优先级最高）

## 引用消息识别
- 格式: [引用 @发送者: 内容片段] 回复内容
- 引用消息应归入被引用消息所在线程
- 若被引用消息不在当前批次，在 notes 中说明

输出必须是 JSON，不要包含 Markdown 或多余文本。"""

USER_PROMPT_V2 = """消息列表(格式: [消息ID] 时间 发送者: 内容):
{messages}

要求:
1) summary 为 100-200 字中文摘要
2) 若有辩论，请包含正反方观点
3) time_range 仅输出时间范围 (HH:MM)
4) message_ids 覆盖该话题所有消息
5) confidence 为 0-1
6) notes 说明归类依据
"""
```

**验收**：v2 输出稳定包含 `message_ids`、`confidence`、`notes`。

### Step 5: 数据模型扩展

**目标**：支持新字段并保持兼容

**修改文件**：`src/models/llm_analysis.py`

```python
message_ids: list[str] = Field(default_factory=list, description="消息ID列表")
confidence: float = Field(default=1.0, ge=0, le=1, description="归类置信度")
notes: str = Field(default="", description="归类依据说明")
```

**验收**：旧输出仍可反序列化，新字段有默认值。

### Step 6: 分析流程接入

**目标**：在格式化时展示引用关系，且带 `msg_id`

**修改文件**：`src/services/llm/analysis.py`

```python
def _format_message_line(self, message: dict[str, Any]) -> str:
    time_str = self._format_timestamp(message.get("create_time"))
    sender = message.get("chatroom_sender") or message.get("from_username") or "unknown"
    msg_id = message.get("msg_id", "")
    content = str(message.get("content") or "").replace("\n", " ").strip()

    refermsg = message.get("refermsg")
    if refermsg and self.config.analysis.enable_refermsg_display:
        ref_content = (refermsg.get("content") or "")[:30]
        ref_display = f"[引用 @{refermsg.get('displayname', '?')}: {ref_content}...]"
        reply_content = message.get("appmsg_title", "")
        content = f\"{ref_display} {reply_content}\"

    if self.config.analysis.prompt_version == "v2":
        return f"[{msg_id}] {time_str} {sender}: {content}"
    return f"{time_str} {sender}: {content}"
```

**验收**：v2 格式包含 `[msg_id]` 且引用消息可读。

### Step 7: 配置开关与默认值

**目标**：可切换解析与提示词版本

**修改文件**：`src/services/llm/config.py`、`config/llm.yaml`

```yaml
analysis:
  max_messages_per_batch: null
  max_content_length: null
  enable_xml_parsing: true
  enable_refermsg_display: true
  prompt_version: "v2"
```

**验收**：可通过配置降级至 v1。

### Step 8: 测试与验收

**单元测试**：`tests/unit/lib/test_xml_parser.py`

```python
def test_parse_refermsg_success():
    xml = """<msg><appmsg><title>回复内容</title><type>57</type>
    <refermsg><svrid>123</svrid><type>1</type><content>原始消息</content>
    <displayname>Alice</displayname><createtime>1</createtime></refermsg>
    </appmsg></msg>"""
    result = parse_appmsg_content(xml)
    assert result and result.refermsg and result.refermsg.displayname == "Alice"
```

**集成验证**：

```bash
.venv/bin/diting analyze-chatrooms -d 2026-01-25
```

**验收标准**：
- 引用消息被归入正确话题
- JSON 输出包含 `message_ids`、`confidence`、`notes`
- summary 满足 100-200 字要求

## 交付清单

- `src/lib/xml_parser.py`
- `src/services/llm/message_enricher.py`
- `src/services/llm/prompts.py`
- `src/services/llm/analysis.py`
- `src/models/llm_analysis.py`
- `src/services/llm/config.py`
- `config/llm.yaml`
- `tests/unit/lib/test_xml_parser.py`
