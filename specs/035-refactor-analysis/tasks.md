# Tasks: 重构 analysis.py 模块

**Input**: Design documents from `/specs/035-refactor-analysis/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md

**Tests**: 测试任务不包含在本次重构中，因为规格说明中明确指出"添加新的测试用例（除非验证重构正确性所必需）"属于范围外。重构的验证依赖现有测试套件。

**Organization**: 任务按用户故事组织，每个故事可独立实现和测试。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 任务所属用户故事（US1, US2, US3, US4）
- 包含精确的文件路径

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- 本项目使用单项目结构

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 项目初始化和基础结构准备

- [x] T001 备份原始 analysis.py 文件到 src/services/llm/analysis.py.backup
- [x] T002 验证现有测试套件运行正常：uv run pytest tests/unit/services/llm/ -v

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 创建基础工具模块，所有用户故事都依赖这些模块

**⚠️ CRITICAL**: 所有用户故事工作必须在此阶段完成后才能开始

- [x] T003 [P] 创建 time_utils.py 模块，迁移时间处理函数（to_datetime, extract_times, time_to_seconds, format_time, build_date_range, build_time_range）到 src/services/llm/time_utils.py
- [x] T004 [P] 创建 debug_writer.py 模块，实现 DebugWriter 类（debug_write, safe_dirname, format_keywords, write_merge_report, format_topics_for_debug, format_chunk_summary_for_debug, format_merged_summary_for_debug, render_batch_debug_header）到 src/services/llm/debug_writer.py
- [x] T005 验证基础模块：运行 uv run mypy src/services/llm/time_utils.py src/services/llm/debug_writer.py

**Checkpoint**: 基础工具模块就绪 - 用户故事实现可以并行开始

---

## Phase 3: User Story 1 - 开发者维护和扩展分析模块 (Priority: P1) 🎯 MVP

**Goal**: 将 analysis.py 拆分为职责单一的模块，每个模块 100-200 行，方法数 5-10 个

**Independent Test**: 检查每个新模块的行数（wc -l）、方法数量（grep "def "）、依赖关系（import 语句）

### Implementation for User Story 1

- [x] T006 [P] [US1] 创建 message_formatter.py 模块，实现 MessageFormatter 类和工具函数（ensure_message_ids, assign_sequence_ids, load_image_ocr_cache, format_message_line, format_message_line_for_summary）到 src/services/llm/message_formatter.py
- [x] T007 [P] [US1] 创建 message_batcher.py 模块，实现 MessageBatcher 类（split_messages_by_count, split_messages_by_tokens, estimate_tokens）到 src/services/llm/message_batcher.py
- [x] T008 [P] [US1] 创建 llm_client.py 模块，定义 LLMProvider Protocol，实现 LangChainProvider 和 LLMClient 类（build_llm, invoke_with_retry, parse_response, resolve_message_ids, parse_indices）到 src/services/llm/llm_client.py
- [x] T009 [P] [US1] 创建 topic_merger.py 模块，定义 MergeStrategy Protocol，实现 KeywordSimilarityStrategy 和 TopicMerger 类（normalize_keyword, keyword_similarity, merge_topics, merge_decision, combine_topics, merge_confidence, merge_notes, pick_summary, merge_time_range）到 src/services/llm/topic_merger.py
- [x] T010 [US1] 创建 topic_summarizer.py 模块，实现 TopicSummarizer 类（summarize_topics, summarize_cluster, summarize_chunk, merge_chunk_summaries, chunk_messages_for_summary, select_messages_for_summary, extract_participants）到 src/services/llm/topic_summarizer.py
- [x] T011 [US1] 重构 analysis.py，保留 IMAGE_CONTENT_PATTERN、_topic_popularity、ChatroomMessageAnalyzer 类（作为协调器）、analyze_chatrooms_from_parquet 函数，委托新模块完成具体工作，更新 src/services/llm/analysis.py
- [x] T012 [US1] 更新 __init__.py，确保公共 API 导出（analyze_chatrooms_from_parquet, ChatroomMessageAnalyzer, IMAGE_CONTENT_PATTERN）到 src/services/llm/__init__.py
- [x] T013 [US1] 验证模块行数：wc -l src/services/llm/*.py，确认每个新模块 100-200 行
- [x] T014 [US1] 验证方法数量：grep "def " src/services/llm/*.py | wc -l，确认每个模块 5-10 个方法
- [x] T015 [US1] 运行类型检查：uv run mypy src/services/llm/
- [x] T016 [US1] 运行代码检查：uv run ruff check src/services/llm/
- [x] T017 [US1] 验证现有测试套件通过：uv run pytest tests/unit/services/llm/ -v
- [x] T018 [US1] 验证向后兼容性：python -c "from src.services.llm.analysis import analyze_chatrooms_from_parquet, IMAGE_CONTENT_PATTERN, ChatroomMessageAnalyzer; print('OK')"

**Checkpoint**: User Story 1 完成 - 模块已拆分，代码可维护性显著提升

---

## Phase 4: User Story 2 - 开发者为分析模块编写单元测试 (Priority: P2)

**Goal**: 验证新模块支持独立单元测试，无需真实 LLM API 调用

**Independent Test**: 为每个新模块编写 Mock 测试，验证可以注入 Mock 对象

### Implementation for User Story 2

- [ ] T019 [P] [US2] 创建 time_utils 单元测试示例，演示模块级函数的独立测试到 tests/unit/services/llm/test_time_utils.py
- [ ] T020 [P] [US2] 创建 llm_client 单元测试示例，演示 Protocol 模式的 Mock 注入到 tests/unit/services/llm/test_llm_client.py
- [ ] T021 [P] [US2] 创建 topic_merger 单元测试示例，演示策略模式的 Mock 注入到 tests/unit/services/llm/test_topic_merger.py
- [ ] T022 [P] [US2] 创建 message_formatter 单元测试示例，演示独立测试消息格式化逻辑到 tests/unit/services/llm/test_message_formatter.py
- [ ] T023 [US2] 运行新增单元测试：uv run pytest tests/unit/services/llm/test_time_utils.py tests/unit/services/llm/test_llm_client.py tests/unit/services/llm/test_topic_merger.py tests/unit/services/llm/test_message_formatter.py -v
- [ ] T024 [US2] 验证测试覆盖率：uv run pytest tests/unit/services/llm/ --cov=src/services/llm --cov-report=term-missing

**Checkpoint**: User Story 2 完成 - 新模块可独立测试，无需真实 API 调用

---

## Phase 5: User Story 3 - 开发者扩展 LLM 提供者 (Priority: P3)

**Goal**: 验证 Protocol 设计支持添加新的 LLM 提供者

**Independent Test**: 创建一个新的 LLMProvider 实现并注入到 LLMClient 中

### Implementation for User Story 3

- [ ] T025 [US3] 创建示例：自定义 LLM 提供者实现（MockProvider），演示如何实现 LLMProvider Protocol 到 tests/unit/services/llm/test_custom_provider.py
- [ ] T026 [US3] 创建示例：自定义合并策略实现（MockMergeStrategy），演示如何实现 MergeStrategy Protocol 到 tests/unit/services/llm/test_custom_strategy.py
- [ ] T027 [US3] 更新 quickstart.md，添加扩展指南示例代码到 specs/035-refactor-analysis/quickstart.md
- [ ] T028 [US3] 验证扩展示例运行正常：uv run pytest tests/unit/services/llm/test_custom_provider.py tests/unit/services/llm/test_custom_strategy.py -v

**Checkpoint**: User Story 3 完成 - Protocol 设计验证成功，支持扩展

---

## Phase 6: User Story 4 - 现有功能保持向后兼容 (Priority: P1)

**Goal**: 确保重构后所有公共 API 保持向后兼容

**Independent Test**: 运行现有测试套件和验证导入语句

### Implementation for User Story 4

- [ ] T029 [US4] 验证公共 API 导入：python -c "from src.services.llm.analysis import analyze_chatrooms_from_parquet; print('analyze_chatrooms_from_parquet OK')"
- [ ] T030 [US4] 验证类导入：python -c "from src.services.llm.analysis import ChatroomMessageAnalyzer; print('ChatroomMessageAnalyzer OK')"
- [ ] T031 [US4] 验证常量导入：python -c "from src.services.llm.analysis import IMAGE_CONTENT_PATTERN; print('IMAGE_CONTENT_PATTERN OK')"
- [ ] T032 [US4] 运行完整测试套件：uv run pytest tests/unit/services/llm/ -v
- [ ] T033 [US4] 验证集成测试（如果存在）：uv run pytest tests/integration/ -k llm -v || echo "No integration tests"
- [ ] T034 [US4] 验证代码行数减少：wc -l src/services/llm/analysis.py（目标约 250 行）

**Checkpoint**: User Story 4 完成 - 向后兼容性验证通过

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 最终优化和文档更新

- [ ] T035 [P] 添加模块级 docstring 到所有新模块（time_utils.py, debug_writer.py, message_formatter.py, message_batcher.py, llm_client.py, topic_merger.py, topic_summarizer.py）
- [ ] T036 [P] 更新 CLAUDE.md 中的 Recent Changes 部分，记录重构完成
- [ ] T037 验证所有验证命令：运行 specs/035-refactor-analysis/plan.md 中的 Verification Plan
- [ ] T038 删除备份文件：rm src/services/llm/analysis.py.backup
- [ ] T039 最终代码检查：uv run ruff check src/services/llm/ && uv run mypy src/services/llm/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成 - 阻塞所有用户故事
- **User Stories (Phase 3-6)**: 所有依赖 Foundational 完成
  - US1 (Phase 3): 核心重构，其他故事依赖此故事
  - US2 (Phase 4): 依赖 US1 完成（需要新模块存在）
  - US3 (Phase 5): 依赖 US1 完成（需要 Protocol 定义）
  - US4 (Phase 6): 依赖 US1 完成（需要重构完成）
- **Polish (Phase 7)**: 依赖所有用户故事完成

### User Story Dependencies

- **User Story 1 (P1)**: 在 Foundational 完成后可开始 - 无其他故事依赖
- **User Story 2 (P2)**: 依赖 US1 完成 - 需要新模块存在才能编写测试
- **User Story 3 (P3)**: 依赖 US1 完成 - 需要 Protocol 定义存在
- **User Story 4 (P1)**: 依赖 US1 完成 - 需要重构完成才能验证兼容性

### Within Each User Story

**User Story 1 (核心重构)**:
- T003-T005 (Foundational) 必须先完成
- T006-T009 可并行（不同文件）
- T010 依赖 T006-T009（topic_summarizer 依赖其他模块）
- T011 依赖 T006-T010（analysis.py 重构需要所有新模块）
- T012 依赖 T011（__init__.py 更新需要 analysis.py 完成）
- T013-T018 验证任务按顺序执行

**User Story 2 (测试)**:
- T019-T022 可并行（不同测试文件）
- T023-T024 验证任务按顺序执行

**User Story 3 (扩展)**:
- T025-T026 可并行（不同示例文件）
- T027-T028 按顺序执行

**User Story 4 (兼容性)**:
- T029-T034 按顺序执行（验证任务）

### Parallel Opportunities

- **Foundational Phase**: T003 和 T004 可并行（不同文件）
- **User Story 1**: T006, T007, T008, T009 可并行（不同文件）
- **User Story 2**: T019, T020, T021, T022 可并行（不同测试文件）
- **User Story 3**: T025 和 T026 可并行（不同示例文件）
- **Polish Phase**: T035 和 T036 可并行（不同文件）

---

## Parallel Example: User Story 1 Core Modules

```bash
# 在 Foundational 完成后，并行创建核心模块：
Task: "创建 message_formatter.py 模块到 src/services/llm/message_formatter.py"
Task: "创建 message_batcher.py 模块到 src/services/llm/message_batcher.py"
Task: "创建 llm_client.py 模块到 src/services/llm/llm_client.py"
Task: "创建 topic_merger.py 模块到 src/services/llm/topic_merger.py"

# 然后创建依赖多个模块的 topic_summarizer.py：
Task: "创建 topic_summarizer.py 模块到 src/services/llm/topic_summarizer.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - 阻塞所有故事)
3. Complete Phase 3: User Story 1（核心重构）
4. **STOP and VALIDATE**: 运行所有验证命令
5. 如果验证通过，重构完成，可选择继续 US2-US4

### Incremental Delivery

1. Complete Setup + Foundational → 基础就绪
2. Add User Story 1 → 独立测试 → 核心重构完成（MVP!）
3. Add User Story 2 → 独立测试 → 测试能力增强
4. Add User Story 3 → 独立测试 → 扩展能力验证
5. Add User Story 4 → 独立测试 → 兼容性确认
6. 每个故事增加价值，不破坏之前的故事

### Sequential Strategy (Recommended for Refactoring)

由于这是重构任务，建议按顺序执行：

1. Phase 1-2: Setup + Foundational
2. Phase 3: User Story 1（核心重构，必须完成）
3. Phase 4: User Story 2（可选，增强测试）
4. Phase 5: User Story 3（可选，验证扩展性）
5. Phase 6: User Story 4（必须，验证兼容性）
6. Phase 7: Polish

---

## Notes

- [P] 任务 = 不同文件，无依赖
- [Story] 标签将任务映射到特定用户故事，便于追溯
- 每个用户故事应该可独立完成和测试
- 每个任务或逻辑组后提交代码
- 在每个检查点停止以独立验证故事
- 避免：模糊任务、同文件冲突、破坏独立性的跨故事依赖
- 重构的关键：增量进行，每个阶段后运行测试验证
