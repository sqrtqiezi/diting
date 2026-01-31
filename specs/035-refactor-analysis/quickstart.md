# Quickstart: 重构 analysis.py 模块

**Feature**: 035-refactor-analysis
**Date**: 2026-01-31

## 概述

本指南帮助开发者快速理解重构后的模块结构和使用方式。

## 模块结构

重构后的 `src/services/llm/` 目录结构：

```
src/services/llm/
├── analysis.py              # 主入口（向后兼容）
├── time_utils.py            # 时间处理工具
├── debug_writer.py          # 调试输出
├── message_formatter.py     # 消息格式化
├── message_batcher.py       # 消息分批
├── llm_client.py            # LLM 客户端（Protocol + 工厂模式）
├── topic_merger.py          # 话题合并（策略模式）
└── topic_summarizer.py      # 话题摘要
```

## 使用方式

### 现有代码（无需修改）

```python
# 这些导入继续工作，无需任何修改
from src.services.llm.analysis import analyze_chatrooms_from_parquet
from src.services.llm.analysis import ChatroomMessageAnalyzer
from src.services.llm.analysis import IMAGE_CONTENT_PATTERN
```

### 新模块的直接使用（可选）

```python
# 时间处理
from src.services.llm.time_utils import to_datetime, format_time

# 消息格式化
from src.services.llm.message_formatter import MessageFormatter

# LLM 客户端（支持依赖注入）
from src.services.llm.llm_client import LLMClient, LLMProvider, LangChainProvider

# 话题合并（支持策略注入）
from src.services.llm.topic_merger import TopicMerger, MergeStrategy
```

## 扩展指南

### 添加新的 LLM 提供者

```python
from src.services.llm.llm_client import LLMProvider, LLMClient

class MyCustomProvider:
    """自定义 LLM 提供者"""

    def invoke(self, messages: list[dict]) -> str:
        # 实现你的 LLM 调用逻辑
        return "response"

# 使用自定义提供者
client = LLMClient(config, provider=MyCustomProvider())
```

### 添加新的合并策略

```python
from src.services.llm.topic_merger import MergeStrategy, TopicMerger

class MyMergeStrategy:
    """自定义合并策略"""

    def should_merge(self, topic1, topic2) -> bool:
        # 实现你的合并逻辑
        return True

# 使用自定义策略
merger = TopicMerger(config, strategy=MyMergeStrategy())
```

## 测试指南

### 运行现有测试

```bash
uv run pytest tests/unit/services/llm/ -v
```

### 使用 Mock 进行单元测试

```python
from unittest.mock import Mock
from src.services.llm.llm_client import LLMClient

def test_with_mock_provider():
    mock_provider = Mock()
    mock_provider.invoke.return_value = "mocked response"

    client = LLMClient(config, provider=mock_provider)
    result = client.invoke_with_retry(messages)

    mock_provider.invoke.assert_called_once()
```

## 验证命令

```bash
# 类型检查
uv run mypy src/services/llm/

# 代码检查
uv run ruff check src/services/llm/

# 导入兼容性验证
python -c "from src.services.llm.analysis import analyze_chatrooms_from_parquet, IMAGE_CONTENT_PATTERN, ChatroomMessageAnalyzer; print('OK')"
```

## 常见问题

### Q: 重构后性能会变化吗？

A: 不会。重构只改变代码组织结构，不改变功能行为。所有方法的实现逻辑保持不变。

### Q: 需要更新现有的调用代码吗？

A: 不需要。所有公共 API 保持向后兼容，现有导入路径继续工作。

### Q: 如何选择使用哪个模块？

A:
- 如果你只是使用分析功能，继续使用 `analysis.py` 的公共 API
- 如果你需要自定义 LLM 提供者或合并策略，直接导入相应模块
