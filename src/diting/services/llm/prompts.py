"""LLM 提示词模板"""

SYSTEM_PROMPT_V1 = (
    "你是微信群聊分析助手。请根据聊天记录，按话题聚合并分类。"
    "输出必须严格遵循协议格式，不得输出任何额外文本。"
    "协议规则: 必须包含 <<<RESULT_START>>> 和 <<<RESULT_END>>>; "
    "每个话题块以 <<<TOPIC>>> 开始; "
    "字段名固定为 keywords/participants/message_indices/message_count/confidence/notes; "
    "每个字段单行 key: value; "
    "列表字段 keywords/participants/message_indices 必须用多行且以 '- ' 开头。"
)

SYSTEM_PROMPT_V2 = """你是微信群聊分析助手。请根据聊天记录，按话题聚合并分类。

## 主题线索切分规则
1. 引用关系: 通过 [引用] 标记识别（优先级最高）
2. 问答关系: 明确的提问-回答对
3. 语义相似性: 讨论同一主题或关键词
4. 时间邻近性: 仅作为弱信号使用，不应主导拆分

## 引用消息识别
- 格式: [引用 @发送者: 内容片段] 回复内容
- 引用消息应归入被引用消息所在线索
- 若被引用消息不在当前批次，在 notes 中说明

## 置信度说明
- 0.85-1.0: 明确的引用/问答关系
- 0.6-0.85: 基于语义相似性的合理推断
- < 0.6: 不稳定，需在 notes 中解释

输出必须严格遵循协议格式，不得输出任何额外文本。
协议规则: 必须包含 <<<RESULT_START>>> 和 <<<RESULT_END>>>; 每个话题块以 <<<TOPIC>>> 开始;
字段名固定为 keywords/participants/message_indices/message_count/confidence/notes;
每个字段单行 key: value;
列表字段 keywords/participants/message_indices 必须用多行且以 '- ' 开头。"""


USER_PROMPT_V1 = (
    "群聊 ID: {chatroom_id}\n"
    "群聊名称: {chatroom_name}\n"
    "分析日期范围: {date_range}\n"
    "消息总数: {total_messages}\n"
    "消息列表(格式: 时间 发送者: 内容):\n"
    "{messages}\n\n"
    "请基于消息内容聚合话题，要求:\n"
    "1) 不要生成话题标题或摘要，仅提炼多个关键词\n"
    "2) keywords 需要覆盖话题核心信息，至少 3 个关键词\n"
    "3) 输出必须严格遵循协议格式，不得输出任何额外文本\n"
    "4) 若无法聚合话题，也必须输出协议格式，且不包含任何 <<<TOPIC>>> 块\n"
    "输出格式示例:\n"
    "<<<RESULT_START>>>\n"
    "<<<TOPIC>>>\n"
    "keywords:\n"
    "- 关键词1\n"
    "- 关键词2\n"
    "- 关键词3\n"
    "participants:\n"
    "- 成员A\n"
    "- 成员B\n"
    "message_indices:\n"
    "- 1-3\n"
    "- 8\n"
    "message_count: 10\n"
    "confidence: 0.85\n"
    "notes: 归类依据说明\n"
    "<<<RESULT_END>>>\n"
)

USER_PROMPT_V2 = """群聊 ID: {chatroom_id}
群聊名称: {chatroom_name}
分析日期范围: {date_range}
消息总数: {total_messages}

消息列表(格式: [序号] 时间 发送者: 内容):
{messages}

请基于消息内容聚合话题，要求:
1) 不要生成话题标题或摘要，仅提炼多个关键词
2) keywords 需要覆盖话题核心信息，至少 3 个关键词
3) message_indices 必须包含该话题的所有消息序号，可使用 1-5 的区间缩写
4) confidence 表示归类置信度 (0-1)
5) notes 说明归类依据
6) 输出必须严格遵循协议格式，不得输出任何额外文本
7) 若无法聚合话题，也必须输出协议格式，且不包含任何 <<<TOPIC>>> 块

输出格式示例:
<<<RESULT_START>>>
<<<TOPIC>>>
keywords:
- 关键词1
- 关键词2
- 关键词3
participants:
- 成员A
- 成员B
message_indices:
- 1-3
- 8
message_count: 10
confidence: 0.92
notes: 归类依据说明
<<<RESULT_END>>>"""


CHUNK_SUMMARY_SYSTEM_PROMPT = """你是微信群聊分析助手。请基于给定消息片段生成摘要。
输出必须严格遵循协议格式，不得输出任何额外文本。
协议规则: 必须包含 <<<RESULT_START>>> 和 <<<RESULT_END>>>; 每个话题块以 <<<TOPIC>>> 开始;
字段名固定为 summary/notes; 每个字段单行 key: value。"""

CHUNK_SUMMARY_USER_PROMPT = """群聊 ID: {chatroom_id}
群聊名称: {chatroom_name}
分析日期范围: {date_range}
关键词: {keywords}
分段: {chunk_index}/{chunk_total}
片段消息数: {total_messages}

消息列表(格式: 时间 发送者: 内容):
{messages}

请完成:
1) summary 为 80-150 字中文摘要
2) notes 用于说明归纳依据（可为空）
3) 若片段包含观点/分歧/因果/影响，请在 summary 中保留要点

输出格式示例:
<<<RESULT_START>>>
<<<TOPIC>>>
summary: 片段摘要
notes: 归纳依据说明
<<<RESULT_END>>>"""

MERGE_SUMMARY_SYSTEM_PROMPT = """你是微信群聊分析助手。请根据多个分段摘要生成最终话题总结。
输出必须严格遵循协议格式，不得输出任何额外文本。
协议规则: 必须包含 <<<RESULT_START>>> 和 <<<RESULT_END>>>; 每个话题块以 <<<TOPIC>>> 开始;
字段名固定为 title/category/summary/notes; 每个字段单行 key: value。"""

MERGE_SUMMARY_USER_PROMPT = """群聊 ID: {chatroom_id}
群聊名称: {chatroom_name}
分析日期范围: {date_range}
关键词: {keywords}
分段摘要数量: {chunk_total}

分段摘要:
{chunk_summaries}

请完成:
1) title 为简洁话题标题
2) category 只能为: 时事 / 投资理财 / 工作生活 / 迪子
3) 分类优先级与规则:
   - 若与 比亚迪/迪子/朝阳老师/91迪先生/迪链 强相关，优先归为 迪子（即便涉及投资）
   - 若同时涉及时事与市场影响，以讨论重心为准:
     - 决策/行情/交易 -> 投资理财
     - 事件本身/社会影响 -> 时事
   - 娱乐、科技产品体验、社交互动等 -> 工作生活
4) summary 风格要求:
   - 时事/投资理财: 约 120-300 字，提炼观点、分歧、因果或影响，尽量给出群内主要立场或洞察
   - 工作生活: 约 80-120 字，言简意赅
   - 迪子: 约 80-120 字，语气轻松愉悦，带一点调侃
5) notes 用于说明归纳依据（可为空）

输出格式示例:
<<<RESULT_START>>>
<<<TOPIC>>>
title: 话题标题
category: 时事
summary: 话题摘要(100-200字)
notes: 归类依据说明
<<<RESULT_END>>>"""


def get_prompts(version: str = "v1") -> tuple[str, str]:
    """获取指定版本的提示词"""
    if version.lower() == "v2":
        return SYSTEM_PROMPT_V2, USER_PROMPT_V2
    return SYSTEM_PROMPT_V1, USER_PROMPT_V1


def get_summary_prompts() -> tuple[str, str, str, str]:
    """获取分段与合并摘要提示词"""
    return (
        CHUNK_SUMMARY_SYSTEM_PROMPT,
        CHUNK_SUMMARY_USER_PROMPT,
        MERGE_SUMMARY_SYSTEM_PROMPT,
        MERGE_SUMMARY_USER_PROMPT,
    )
