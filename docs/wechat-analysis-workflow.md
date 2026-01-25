# 微信群聊消息总结流程

本文说明 diting 的微信群聊消息分析与报告生成全流程，覆盖数据读取、引用消息解析、LLM 提示词协议、解析与报告输出。

## 1. 数据来源与格式

- 原始消息: `data/messages/raw/*.jsonl`
- 入库格式: `data/messages/parquet/` 按日期分区
- 查询方式: 按日期与 `is_chatroom_msg=1` 过滤

## 2. 分析入口

- CLI: `diting analyze-chatrooms -d YYYY-MM-DD [--chatroom <id>...] [--output <path>]`
- 日期为单日分析区间
- `--chatroom` 可限制特定群聊

## 3. 读取与过滤

读取 Parquet 中以下字段:
- `chatroom`, `chatroom_sender`, `from_username`
- `content`, `create_time`, `msg_id`, `msg_type`
- `is_chatroom_msg`

仅保留群聊消息(`is_chatroom_msg=1`)。

## 4. 引用消息解析

对 `msg_type=49` 的消息解析 XML:
- 提取 `appmsg_type`, `refermsg`
- 若为引用消息(`appmsg_type=57`)，补充:
  - `refermsg.displayname`, `refermsg.content`, `refermsg.createtime`
- 在提示词中以引用格式展示:
  - `[引用 @昵称: 内容片段] 回复内容`

## 5. 批次切分

- 优先按 token 估算切分，避免超长输入
- 若配置 `max_messages_per_batch`，则限制每批最大消息数

## 6. 批次提取协议(分隔符 + 键值行)

LLM 输出必须遵循协议格式:
- 必须包含 `<<<RESULT_START>>>` 与 `<<<RESULT_END>>>`
- 每个话题块以 `<<<TOPIC>>>` 开始
- 每个字段单行 `key: value`
- 列表字段 `participants` 与 `message_indices` 使用 `- ` 多行

字段清单:
- `keywords`
- `participants`, `message_indices`, `message_count`
- `confidence`, `notes`

说明:
- `message_indices` 为消息序号，可使用区间缩写(例如 `1-5`)以减少输出长度

## 7. 响应解析

解析器按协议分块:
- 以 `<<<TOPIC>>>` 切分话题块
- 解析 `key: value` 与列表字段
- 生成 `TopicClassification` 列表
- 解析失败时记录 warning，不影响其它话题

## 8. 跨批合并与摘要生成

在批次聚合后，会对话题进行跨批合并：
- 依据关键词相似度合并
- 时间邻近性不作为合并主因

合并完成后，使用二次摘要流程：
1) 对每个话题按片段生成分段摘要
2) 再合并分段摘要生成最终 `title/category/summary/notes`

## 9. 热门度与排序

对每个话题计算热门度:
- `U = 参与人数(去重)`
- `M = 消息数量`
- `Hot = ln(1+U)^1.2 * ln(1+M)^0.8 * (1 / (1 + max(0, M/U - 6))^0.4)`

按热门度降序，输出 Top 10。

## 10. 报告输出

- Markdown 报告包含:
  - 分析日期、生成时间
  - 群聊信息、消息总数、话题总数
  - 热门话题表格与摘要
- 通过 `--output` 写入文件，否则输出到终端

## 11. 批次调试输出

使用 `--debug-dir` 输出中间结果，结构示例:

```
debug/
  38733837988_chatroom/
    batch_01_input.txt
    batch_01_output.txt
    batch_01_topics.txt
    batch_02_input.txt
    batch_02_output.txt
    batch_02_topics.txt
    merge_report.txt
```

- `batch_*_input.txt`: 本批次输入消息文本
- `batch_*_output.txt`: 模型原始输出
- `batch_*_topics.txt`: 解析后的话题结构
- `merge_report.txt`: 话题合并记录（含合并原因与相似度）

## 12. 关键文件

- `src/services/llm/analysis.py` 分析主流程
- `src/services/llm/prompts.py` 提示词协议
- `src/services/llm/response_parser.py` 协议解析
- `src/services/llm/message_enricher.py` 引用消息解析
- `cli.py` 报告生成与输出
