# Implementation Plan: 重构 analysis.py 模块

**Branch**: `035-refactor-analysis` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/035-refactor-analysis/spec.md`

## Summary

将 `src/services/llm/analysis.py`（1176 行，约 40 个方法）拆分为 7 个职责单一的模块，采用 Protocol + 工厂模式和策略模式提高可测试性和可扩展性，同时保持向后兼容。

## Technical Context

**Language/Version**: Python 3.12.6
**Primary Dependencies**: LangChain (langchain-openai), pandas, structlog, tiktoken
**Storage**: N/A（纯代码重构，不涉及存储变更）
**Testing**: pytest（现有测试套件 `tests/unit/services/llm/`）
**Target Platform**: Linux server / macOS
**Project Type**: single
**Performance Goals**: N/A（行为不变，性能保持一致）
**Constraints**: 向后兼容（现有导入路径必须继续工作）
**Scale/Scope**: 1 个文件拆分为 8 个文件（1 个主文件 + 7 个新模块）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Privacy First** | ✅ PASS | 纯代码重构，不涉及数据处理变更 |
| **II. Endpoint Modularity** | ✅ PASS | 重构提高模块化程度，符合原则 |
| **III. Knowledge Graph Core** | ✅ N/A | 不涉及知识图谱功能 |
| **IV. LLM-Powered Insights** | ✅ PASS | Protocol 设计支持多模型切换，符合原则 |
| **V. Observability & Testability** | ✅ PASS | 拆分后模块可独立测试，提高可测试性 |

**Gate Result**: ✅ PASS - 所有相关原则均符合

## Project Structure

### Documentation (this feature)

```text
specs/035-refactor-analysis/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (N/A for refactoring)
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/services/llm/
├── __init__.py              # 更新：导出公共 API
├── analysis.py              # 重构：主分析器（精简后约 250 行）
├── config.py                # 现有：配置管理
├── prompts.py               # 现有：提示词模板
├── response_parser.py       # 现有：响应解析
├── message_enricher.py      # 现有：消息增强
├── time_utils.py            # 新建：时间处理工具
├── debug_writer.py          # 新建：调试输出
├── message_formatter.py     # 新建：消息格式化与预处理
├── message_batcher.py       # 新建：消息分批策略
├── llm_client.py            # 新建：LLM 客户端封装（含协议定义）
├── topic_merger.py          # 新建：话题合并逻辑
└── topic_summarizer.py      # 新建：话题摘要生成

tests/unit/services/llm/
├── __init__.py
├── test_analysis_image_ocr.py  # 现有测试
├── test_time_utils.py          # 新建（可选）
├── test_message_formatter.py   # 新建（可选）
├── test_topic_merger.py        # 新建（可选）
└── test_llm_client.py          # 新建（可选）
```

**Structure Decision**: 使用现有的单项目结构，在 `src/services/llm/` 目录下新增 7 个模块文件。

## Complexity Tracking

> 无违规项 - 重构完全符合宪章原则

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Module Design

### 模块依赖关系图

```
analysis.py (主入口，约 250 行)
    ├── time_utils.py (独立，约 80 行)
    ├── debug_writer.py (独立，约 150 行)
    ├── message_formatter.py (约 120 行)
    │   └── time_utils.py
    ├── message_batcher.py (约 80 行)
    │   └── message_formatter.py
    ├── llm_client.py (约 150 行)
    │   └── response_parser.py (现有)
    ├── topic_merger.py (约 200 行)
    │   └── time_utils.py
    └── topic_summarizer.py (约 250 行)
        ├── llm_client.py
        ├── message_formatter.py
        ├── time_utils.py
        └── debug_writer.py
```

### 方法迁移映射

| 原方法 | 目标模块 | 新名称/类 |
|--------|----------|-----------|
| `_to_datetime`, `_extract_times`, `_time_to_seconds`, `_format_time` | time_utils.py | 模块级函数 |
| `_build_date_range`, `_build_time_range` | time_utils.py | 模块级函数 |
| `_debug_write`, `_safe_dirname`, `_format_keywords` | debug_writer.py | `DebugWriter` 类 |
| `_write_merge_report`, `_format_topics_for_debug` | debug_writer.py | `DebugWriter` 类 |
| `_format_chunk_summary_for_debug`, `_format_merged_summary_for_debug` | debug_writer.py | `DebugWriter` 类 |
| `_render_batch_debug_header` | debug_writer.py | `DebugWriter` 类 |
| `_ensure_message_ids`, `_assign_sequence_ids` | message_formatter.py | 模块级函数 |
| `_load_image_ocr_cache` | message_formatter.py | 模块级函数 |
| `_format_message_line`, `_format_message_line_for_summary` | message_formatter.py | `MessageFormatter` 类 |
| `_split_messages_by_count`, `_split_messages_by_tokens` | message_batcher.py | `MessageBatcher` 类 |
| `_estimate_tokens` | message_batcher.py | `MessageBatcher` 类 |
| `_build_llm` | llm_client.py | `LangChainProvider` 类 |
| `_invoke_with_retry` | llm_client.py | `LLMClient` 类 |
| `_parse_response`, `_resolve_message_ids`, `_parse_indices` | llm_client.py | `LLMClient` 类 |
| `_normalize_keyword`, `_keyword_similarity` | topic_merger.py | 模块级函数 |
| `_merge_topics`, `_merge_decision`, `_combine_topics` | topic_merger.py | `TopicMerger` 类 |
| `_merge_confidence`, `_merge_notes`, `_pick_summary`, `_merge_time_range` | topic_merger.py | `TopicMerger` 类 |
| `_summarize_topics`, `_summarize_cluster`, `_summarize_chunk` | topic_summarizer.py | `TopicSummarizer` 类 |
| `_merge_chunk_summaries`, `_chunk_messages_for_summary` | topic_summarizer.py | `TopicSummarizer` 类 |
| `_select_messages_for_summary`, `_extract_participants` | topic_summarizer.py | `TopicSummarizer` 类 |

### 保留在 analysis.py 的内容

- `IMAGE_CONTENT_PATTERN` 常量
- `_topic_popularity` 函数
- `ChatroomMessageAnalyzer` 类（作为协调器）
  - `__init__` 方法（初始化各模块）
  - `analyze_chatroom` 方法（主入口）
  - `_analyze_batch` 方法（批次分析）
- `analyze_chatrooms_from_parquet` 函数（公共 API）

## Implementation Phases

### Phase 1: 基础工具模块（无依赖）

1. **time_utils.py** - 时间处理工具
2. **debug_writer.py** - 调试输出

### Phase 2: 消息处理模块

3. **message_formatter.py** - 消息格式化（依赖 time_utils）
4. **message_batcher.py** - 消息分批（依赖 message_formatter）

### Phase 3: LLM 交互模块

5. **llm_client.py** - LLM 客户端（依赖 response_parser）

### Phase 4: 话题处理模块

6. **topic_merger.py** - 话题合并（依赖 time_utils）
7. **topic_summarizer.py** - 话题摘要（依赖多个模块）

### Phase 5: 主分析器重构

8. **analysis.py** - 精简主分析器，委托各模块
9. **__init__.py** - 更新导出

## Verification Plan

```bash
# 1. 运行现有测试确保不破坏功能
uv run pytest tests/unit/services/llm/ -v

# 2. 运行类型检查
uv run mypy src/services/llm/

# 3. 运行代码检查
uv run ruff check src/services/llm/

# 4. 验证导入兼容性
python -c "from src.services.llm.analysis import analyze_chatrooms_from_parquet, IMAGE_CONTENT_PATTERN, ChatroomMessageAnalyzer; print('OK')"

# 5. 验证模块行数
wc -l src/services/llm/*.py
```

## Risk Mitigation

| 风险 | 缓解措施 |
|------|----------|
| 循环依赖 | 使用依赖注入和延迟导入 |
| 测试失败 | 每个阶段后运行测试，增量验证 |
| 导入路径变更 | 在 analysis.py 中保留所有公共 API |
| 类型检查失败 | 使用 Protocol 定义接口，确保类型安全 |
