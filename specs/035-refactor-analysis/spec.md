# Feature Specification: 重构 analysis.py 模块

**Feature Branch**: `035-refactor-analysis`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "根据 docs/todo/refactor-analysis-module.md 中的设计开始重构工作"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 开发者维护和扩展分析模块 (Priority: P1)

作为开发者，我需要能够轻松理解、维护和扩展聊天室消息分析功能。当前 `analysis.py` 文件有 1177 行代码，`ChatroomMessageAnalyzer` 类包含约 40 个方法，职责过多，难以定位和修改特定功能。

**Why this priority**: 这是重构的核心价值——提高代码可维护性。职责单一的模块让开发者能快速定位代码、理解逻辑、进行修改，是后续所有开发工作的基础。

**Independent Test**: 可以通过检查每个新模块的行数（目标 100-200 行）、方法数量（目标 5-10 个）、以及模块间依赖关系来验证。

**Acceptance Scenarios**:

1. **Given** 重构后的模块结构，**When** 开发者需要修改时间处理逻辑，**Then** 只需查看 `time_utils.py` 一个文件即可完成修改
2. **Given** 重构后的模块结构，**When** 开发者需要修改 LLM 调用逻辑，**Then** 只需查看 `llm_client.py` 一个文件即可完成修改
3. **Given** 重构后的模块结构，**When** 开发者需要修改话题合并算法，**Then** 只需查看 `topic_merger.py` 一个文件即可完成修改

---

### User Story 2 - 开发者为分析模块编写单元测试 (Priority: P2)

作为开发者，我需要能够为分析模块的各个功能编写独立的单元测试，而不需要模拟整个 LLM 调用流程。

**Why this priority**: 可测试性是代码质量的重要保障。拆分后的模块可以独立测试，降低测试复杂度，提高测试覆盖率。

**Independent Test**: 可以通过为每个新模块编写独立的单元测试来验证，测试不需要真实的 LLM API 调用。

**Acceptance Scenarios**:

1. **Given** `LLMClient` 类使用 Protocol 模式，**When** 编写单元测试，**Then** 可以注入 Mock 的 `LLMProvider` 进行测试，无需真实 API 调用
2. **Given** `TopicMerger` 类使用策略模式，**When** 编写单元测试，**Then** 可以注入不同的合并策略进行测试
3. **Given** `MessageFormatter` 类独立存在，**When** 编写单元测试，**Then** 可以直接测试消息格式化逻辑，无需依赖其他模块

---

### User Story 3 - 开发者扩展 LLM 提供者 (Priority: P3)

作为开发者，我需要能够轻松添加新的 LLM 提供者（如 Anthropic Claude、本地 Ollama 模型），而不需要修改现有的分析逻辑。

**Why this priority**: 可扩展性是长期维护的关键。Protocol + 工厂模式让添加新的 LLM 提供者变得简单，只需实现接口即可。

**Independent Test**: 可以通过创建一个新的 `LLMProvider` 实现类并注入到 `LLMClient` 中来验证。

**Acceptance Scenarios**:

1. **Given** `LLMProvider` Protocol 定义，**When** 需要添加 Anthropic Claude 支持，**Then** 只需创建 `AnthropicProvider` 类实现 `invoke` 方法
2. **Given** `LLMClient` 支持依赖注入，**When** 创建新的 Provider 实现，**Then** 可以通过构造函数注入到 `LLMClient` 中使用

---

### User Story 4 - 现有功能保持向后兼容 (Priority: P1)

作为现有代码的使用者，我需要在重构后仍然能够使用原有的导入方式和 API，不需要修改任何调用代码。

**Why this priority**: 向后兼容是重构的基本要求，确保重构不会破坏现有功能和依赖。

**Independent Test**: 可以通过运行现有测试套件和验证导入语句来确认。

**Acceptance Scenarios**:

1. **Given** 重构完成后，**When** 使用 `from src.services.llm.analysis import analyze_chatrooms_from_parquet`，**Then** 导入成功且功能正常
2. **Given** 重构完成后，**When** 使用 `from src.services.llm.analysis import ChatroomMessageAnalyzer`，**Then** 导入成功且功能正常
3. **Given** 重构完成后，**When** 使用 `from src.services.llm.analysis import IMAGE_CONTENT_PATTERN`，**Then** 导入成功且值正确

---

### Edge Cases

- 当模块之间存在循环依赖时，如何处理？（需要通过依赖注入或延迟导入解决）
- 当某个模块的方法被多个其他模块使用时，如何确定归属？（按主要职责归类，必要时创建共享工具模块）
- 当重构过程中发现原有代码的 bug 时，如何处理？（记录但不在本次重构中修复，保持行为一致）

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 将 `analysis.py` 拆分为 7 个独立模块：`time_utils.py`、`debug_writer.py`、`message_formatter.py`、`message_batcher.py`、`llm_client.py`、`topic_merger.py`、`topic_summarizer.py`
- **FR-002**: 系统 MUST 保持 `analysis.py` 作为主入口，精简后约 250 行
- **FR-003**: `llm_client.py` MUST 采用 Protocol + 工厂模式，定义 `LLMProvider` 协议和 `LangChainProvider` 默认实现
- **FR-004**: `topic_merger.py` MUST 采用策略模式，定义 `MergeStrategy` 协议和 `KeywordSimilarityStrategy` 默认实现
- **FR-005**: `message_formatter.py` MUST 支持不同的格式化风格（v1、v2），通过配置选择
- **FR-006**: 系统 MUST 保持以下导入向后兼容：`analyze_chatrooms_from_parquet`、`ChatroomMessageAnalyzer`、`IMAGE_CONTENT_PATTERN`
- **FR-007**: 每个新模块 MUST 职责单一，代码行数控制在 100-200 行
- **FR-008**: 系统 MUST 通过现有测试套件验证功能正确性
- **FR-009**: 系统 MUST 通过类型检查（mypy）和代码检查（ruff）

### Key Entities

- **LLMProvider**: LLM 提供者协议，定义统一的 `invoke` 接口，支持不同的 LLM 实现
- **LLMClient**: LLM 客户端，封装重试逻辑和响应解析，支持依赖注入
- **MergeStrategy**: 合并策略协议，定义 `should_merge` 接口，支持不同的合并算法
- **TopicMerger**: 话题合并器，使用策略模式实现话题合并逻辑
- **MessageFormatter**: 消息格式化器，支持多版本格式化风格
- **MessageBatcher**: 消息分批器，负责消息的分批策略
- **TopicSummarizer**: 话题摘要生成器，负责生成话题摘要
- **DebugWriter**: 调试输出器，负责调试信息的格式化和写入

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 重构后 `analysis.py` 主文件代码行数从 1177 行减少到约 250 行（减少约 80%）
- **SC-002**: 每个新模块代码行数控制在 100-200 行，方法数量控制在 5-10 个
- **SC-003**: 现有测试套件 100% 通过，无功能回归
- **SC-004**: 类型检查（mypy）和代码检查（ruff）100% 通过
- **SC-005**: 向后兼容性验证通过，所有公共 API 导入正常工作
- **SC-006**: 新模块可独立进行单元测试，无需真实 LLM API 调用

## Assumptions

- 现有的 `analysis.py` 代码逻辑正确，重构只改变代码组织结构，不改变功能行为
- 现有测试套件足够覆盖核心功能，可以作为重构正确性的验证依据
- LangChain 将继续作为默认的 LLM 框架，新的 Protocol 设计是为未来扩展预留
- 重构过程中发现的任何 bug 将记录但不在本次重构中修复

## Out of Scope

- 添加新的 LLM 提供者实现（如 AnthropicProvider、LocalLLMProvider）
- 修改现有功能行为或修复已知 bug
- 性能优化
- 添加新的测试用例（除非验证重构正确性所必需）
