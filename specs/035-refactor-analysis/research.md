# Research: 重构 analysis.py 模块

**Date**: 2026-01-31
**Feature**: 035-refactor-analysis

## 研究目标

确认现有代码结构和依赖关系，验证设计文档中的方法迁移计划。

## 现有代码分析

### 文件统计

| 文件 | 行数 | 说明 |
|------|------|------|
| analysis.py | 1176 | 主分析器，需要拆分 |
| config.py | ~150 | 配置管理，保持不变 |
| prompts.py | ~200 | 提示词模板，保持不变 |
| response_parser.py | ~150 | 响应解析，保持不变 |
| message_enricher.py | ~50 | 消息增强，保持不变 |

### 方法分类统计

通过分析 `analysis.py` 中的 40+ 个方法，按职责分类：

| 职责类别 | 方法数量 | 目标模块 |
|----------|----------|----------|
| 时间处理 | 6 | time_utils.py |
| 调试输出 | 8 | debug_writer.py |
| 消息格式化 | 5 | message_formatter.py |
| 消息分批 | 3 | message_batcher.py |
| LLM 交互 | 5 | llm_client.py |
| 话题合并 | 8 | topic_merger.py |
| 话题摘要 | 7 | topic_summarizer.py |
| 主协调器 | 4 | analysis.py (保留) |

### 依赖关系分析

**外部依赖**:
- `langchain.prompts.ChatPromptTemplate` - 提示词模板
- `langchain_openai.ChatOpenAI` - OpenAI 客户端
- `pandas` - 数据处理
- `structlog` - 日志
- `tiktoken` - Token 估算（隐式，通过 LangChain）

**内部依赖**:
- `src.config` - 配置路径
- `src.models.llm_analysis` - 数据模型
- `src.services.llm.config` - LLM 配置
- `src.services.llm.prompts` - 提示词
- `src.services.llm.response_parser` - 响应解析
- `src.services.llm.message_enricher` - 消息增强
- `src.services.storage.query` - 存储查询

## 设计决策确认

### Decision 1: Protocol + 工厂模式用于 LLM 客户端

**Decision**: 采用 Python Protocol 定义 `LLMProvider` 接口，`LangChainProvider` 作为默认实现

**Rationale**:
- Protocol 是 Python 3.8+ 的结构化子类型，无需继承即可实现接口
- 支持依赖注入，便于测试时使用 Mock
- 符合开闭原则，添加新 Provider 无需修改现有代码

**Alternatives considered**:
- ABC (Abstract Base Class): 需要显式继承，不够灵活
- Duck typing: 缺乏类型检查支持

### Decision 2: 策略模式用于话题合并

**Decision**: 采用 `MergeStrategy` Protocol，`KeywordSimilarityStrategy` 作为默认实现

**Rationale**:
- 合并算法可能需要调整或替换
- 策略模式允许运行时切换算法
- 便于 A/B 测试不同合并策略

**Alternatives considered**:
- 硬编码算法: 不够灵活，难以测试
- 配置驱动的 if-else: 代码膨胀，难以维护

### Decision 3: 模块级函数 vs 类方法

**Decision**:
- 无状态的工具函数（如时间处理）使用模块级函数
- 有状态或需要配置的功能使用类

**Rationale**:
- 模块级函数更简单，易于测试
- 类封装状态和配置，提供更好的组织

**Alternatives considered**:
- 全部使用类: 过度设计，增加复杂度
- 全部使用函数: 状态管理困难

### Decision 4: 向后兼容策略

**Decision**: 在 `analysis.py` 中保留所有公共 API，内部委托给新模块

**Rationale**:
- 现有代码无需修改
- 渐进式迁移，降低风险
- 符合 Liskov 替换原则

**Alternatives considered**:
- 在 `__init__.py` 中重新导出: 可能导致循环导入
- 要求调用方更新导入: 破坏向后兼容

## 风险评估

### 已识别风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 循环依赖 | 中 | 高 | 使用依赖注入，避免模块间直接导入 |
| 测试覆盖不足 | 低 | 中 | 现有测试套件验证，增量重构 |
| 类型检查失败 | 中 | 低 | 使用 Protocol 定义接口 |
| 性能回归 | 低 | 中 | 行为不变，仅代码组织变更 |

### 无需澄清的项目

所有设计决策已在原始设计文档 `docs/todo/refactor-analysis-module.md` 中确定，无需额外研究。

## 结论

研究确认设计文档中的方案可行，无需修改。可以进入 Phase 1 设计阶段。
