# Diting 项目重构计划

> 生成日期: 2026-02-01
> 基于: 架构师分析 + 代码审查

## 概述

本计划旨在重构 diting 项目中 **11 个需要改进的 Python 文件**，总计约 **5,500 行代码**。
预计重构后代码行数减少 30%，模块数量增加 15 个，代码可维护性显著提升。

## 重构目标

1. **降低复杂度**: 将大文件拆分为小模块，每个模块 < 200 行
2. **职责单一**: 每个类/函数只做一件事
3. **消除重复**: 提取公共逻辑，减少代码重复
4. **提高可测试性**: 通过依赖注入和接口抽象，便于单元测试
5. **保持覆盖率**: 重构后测试覆盖率 ≥ 80%

---

## 阶段一: 高优先级文件 (4个)

### 1.1 storage_commands.py (746行)

**当前问题:**
- 9 个 CLI 命令混在一个文件
- 重复的错误处理和输出格式化
- 缺少命令级别的单元测试

**重构方案:**

```
src/cli/storage_commands.py (746行)
    ↓ 拆分为
src/cli/storage/
├── __init__.py              # 导出 storage 命令组
├── query_commands.py        # query, query_by_id (~180行)
├── ingestion_commands.py    # dump_parquet, ingest_message (~200行)
├── maintenance_commands.py  # cleanup, archive, validate (~180行)
├── detect_commands.py       # detect_duplicates (~100行)
└── utils.py                 # 公共装饰器和输出格式化 (~80行)
```

**关键重构步骤:**

1. **提取公共装饰器** (`utils.py`)
```python
from functools import wraps
import click
import structlog

logger = structlog.get_logger()

def with_parquet_root(func):
    """自动解析 parquet_root 参数"""
    @wraps(func)
    def wrapper(*args, parquet_root=None, **kwargs):
        if parquet_root is None:
            from src.config import get_messages_parquet_path
            parquet_root = str(get_messages_parquet_path())
        return func(*args, parquet_root=parquet_root, **kwargs)
    return wrapper

def handle_storage_errors(func):
    """统一错误处理"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            click.echo(f"✗ 操作失败: {e}", err=True)
            logger.exception("command_failed", error=str(e))
            raise SystemExit(1)
    return wrapper

class Output:
    """统一输出格式化"""
    @staticmethod
    def success(message: str, **details):
        click.echo(f"✓ {message}")
        for key, value in details.items():
            click.echo(f"  {key}: {value}")

    @staticmethod
    def error(message: str):
        click.echo(f"✗ {message}", err=True)

    @staticmethod
    def table(headers: list[str], rows: list[list]):
        # 表格输出逻辑
        pass
```

2. **拆分命令文件** (`query_commands.py`)
```python
import click
from .utils import with_parquet_root, handle_storage_errors, Output

@click.command("query")
@click.option("--start", required=True, help="开始日期")
@click.option("--end", required=True, help="结束日期")
@click.option("--parquet-root", default=None, help="Parquet 根目录")
@with_parquet_root
@handle_storage_errors
def query(start: str, end: str, parquet_root: str):
    """查询消息"""
    from src.services.storage.query import query_messages

    result = query_messages(parquet_root, start, end)
    Output.success(f"查询到 {len(result)} 条消息")
    # ...
```

**风险评估:** 中等
- ✅ 有契约测试保护存储服务层
- ⚠️ CLI 命令本身缺少单元测试
- 需要保持 CLI 接口不变

**预计工时:** 4 小时

---

### 1.2 client.py (555行) ✅ 已完成

**重构状态:** 已完成 (2026-02-01)

**重构成果:**
- 原文件 555 行 → 重构后 273 行 (-51%)
- 新增 5 个模块：protocols.py, http_client.py, error_handler.py, request_builder.py, response_parser.py
- 所有新模块测试覆盖率 100%
- 向后兼容性验证通过

---

### 1.3 duckdb_manager.py (516行) ✅ 已完成

**重构状态:** 已完成 (2026-02-01)

**重构成果:**
- 原文件 516 行 → 重构后 5 个模块共 203 行 (-61%)
- 新增 4 个模块：
  - `duckdb_base.py` (34 行) - 基础连接管理
  - `image_repository.py` (70 行) - 图片数据操作
  - `checkpoint_repository.py` (28 行) - 检查点数据操作
  - `statistics_repository.py` (23 行) - 统计查询
  - `duckdb_manager.py` (48 行) - Facade 类
- 所有新模块测试覆盖率 96-100%
- 向后兼容性验证通过 (28 个原有测试全部通过)
- 新增 32 个单元测试

**设计模式:**
- Repository 模式：按实体分离数据访问逻辑
- Facade 模式：保持向后兼容的公共 API

---

### 1.4 pdf_renderer.py (879行)

**当前问题:**
- `_build_flowables` 函数 227 行，包含 10+ 个 if-elif 分支
- 混合了 Markdown 解析、PDF 样式、Emoji 处理、字体管理
- **没有测试覆盖**

**重构方案:**

```
src/services/report/pdf_renderer.py (879行)
    ↓ 拆分为
src/services/report/
├── pdf_renderer.py          # 主入口 (~150行)
├── markdown_parser.py       # Markdown 解析 (~100行)
├── element_handlers/        # 元素处理器
│   ├── __init__.py
│   ├── base.py              # 基类和协议 (~50行)
│   ├── heading.py           # 标题处理 (~60行)
│   ├── paragraph.py         # 段落处理 (~60行)
│   ├── table.py             # 表格处理 (~100行)
│   ├── list.py              # 列表处理 (~80行)
│   └── code.py              # 代码块处理 (~60行)
├── emoji_processor.py       # Emoji 处理 (~120行)
├── font_manager.py          # 字体管理 (~80行)
└── style_builder.py         # 样式构建 (~100行)
```

**关键重构步骤:**

1. **定义元素处理器协议** (`element_handlers/base.py`)
```python
from typing import Protocol
from reportlab.platypus import Flowable
from dataclasses import dataclass

@dataclass
class RenderContext:
    styles: dict
    options: "PdfRenderOptions"
    emoji_processor: "EmojiProcessor"
    topic_count: int = 0

class ElementHandler(Protocol):
    def can_handle(self, line: str) -> bool: ...
    def handle(self, line: str, context: RenderContext) -> list[Flowable]: ...
    def lines_consumed(self) -> int: ...
```

2. **实现具体处理器** (`element_handlers/heading.py`)
```python
from reportlab.platypus import Paragraph, Spacer
from .base import ElementHandler, RenderContext

class HeadingHandler(ElementHandler):
    def can_handle(self, line: str) -> bool:
        return line.startswith("# ") or line.startswith("## ")

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        if line.startswith("# "):
            text = line[2:].strip()
            style = context.styles["title"]
        else:
            text = line[3:].strip()
            style = context.styles["heading"]

        formatted = context.emoji_processor.process(text, style.fontSize)
        return [
            Spacer(1, 12),
            Paragraph(formatted, style),
            Spacer(1, 6),
        ]

    def lines_consumed(self) -> int:
        return 1
```

3. **重构主渲染器** (`pdf_renderer.py`)
```python
from .element_handlers import (
    HeadingHandler, ParagraphHandler, TableHandler,
    ListHandler, CodeHandler
)
from .emoji_processor import EmojiProcessor
from .style_builder import StyleBuilder

class MarkdownPdfRenderer:
    def __init__(self, options: PdfRenderOptions):
        self.options = options
        self.emoji_processor = EmojiProcessor(options)
        self.style_builder = StyleBuilder(options)
        self.handlers = [
            HeadingHandler(),
            TableHandler(),
            ListHandler(),
            CodeHandler(),
            ParagraphHandler(),  # 默认处理器，放最后
        ]

    def render(self, markdown: str, output_path: Path) -> None:
        lines = markdown.split("\n")
        styles = self.style_builder.build()
        context = RenderContext(styles, self.options, self.emoji_processor)

        flowables = []
        index = 0
        while index < len(lines):
            line = lines[index]
            for handler in self.handlers:
                if handler.can_handle(line):
                    result = handler.handle(line, context)
                    flowables.extend(result)
                    index += handler.lines_consumed()
                    break
            else:
                index += 1

        self._build_pdf(flowables, output_path)
```

**风险评估:** 高
- ⚠️ **没有测试覆盖**，需要先补充测试
- 功能复杂，涉及 PDF 渲染、Emoji 处理
- 建议先编写集成测试再重构

**预计工时:** 8 小时 (含测试编写)

---

## 阶段二: 中优先级文件 (6个)

### 2.1 analysis.py (386行)

**重构方案:**
- 提取 `AnalysisPipeline` 类编排分析流程
- 提取 `MessagePreprocessor` 处理消息预处理
- 提取 `ResultPostprocessor` 处理结果后处理

**预计工时:** 3 小时

### 2.2 image_extractor.py (375行)

**重构方案:**
- 拆分为 `image_extractor.py`、`parquet_updater.py`、`extraction_checkpoint.py`

**预计工时:** 3 小时

### 2.3 incremental.py (342行)

**重构方案:**
- 创建 `IncrementalIngestionService` 类
- 提取 `DataNormalizer` 和 `MessageExtractor`

**预计工时:** 3 小时

### 2.4 wechat_message_schema.py (333行)

**重构方案:**
- 拆分为 `message_models.py`、`contact_models.py`、`sns_models.py`

**预计工时:** 2 小时

### 2.5 topic_summarizer.py (332行)

**重构方案:**
- 提取 `SummaryPromptManager`、`SummaryGenerator`、`SummaryParser`

**预计工时:** 3 小时

### 2.6 topic_merger.py (320行)

**重构方案:**
- 提取 `KeywordSimilarityCalculator`、`KeywordNormalizer`
- 优化 289 行的 `keyword_similarity` 函数

**预计工时:** 3 小时

---

## 阶段三: 低优先级文件 (1个)

### 3.1 ingestion.py (301行)

**重构方案:**
- 创建 `ParquetConverter` 类
- 提取 `PartitionManager` 类

**预计工时:** 2 小时

---

## 执行计划

### 时间线

```
Week 1: 阶段一 (高优先级)
├── Day 1-2: storage_commands.py
├── Day 3-4: client.py
├── Day 5: duckdb_manager.py
└── Day 6-7: pdf_renderer.py (含测试)

Week 2: 阶段二 (中优先级)
├── Day 1: analysis.py
├── Day 2: image_extractor.py
├── Day 3: incremental.py
├── Day 4: wechat_message_schema.py
├── Day 5: topic_summarizer.py
└── Day 6: topic_merger.py

Week 3: 阶段三 + 收尾
├── Day 1: ingestion.py
├── Day 2-3: 集成测试和回归测试
└── Day 4-5: 文档更新和代码审查
```

### 每个重构的工作流

```bash
# 1. 创建功能分支
git checkout master && git pull
git checkout -b 048-refactor-{module-name}

# 2. 补充测试 (如果缺失)
# 编写测试用例...
uv run pytest tests/unit/test_{module}.py -v

# 3. 执行重构
# 小步重构，每步后运行测试...

# 4. 验证
/local-ci

# 5. 提交
/commit-and-push

# 6. 创建 PR
/create-pr

# 7. 合并
/merge-pr
```

---

## 风险管理

### 高风险项

| 文件 | 风险 | 缓解措施 |
|------|------|----------|
| pdf_renderer.py | 无测试 | 先编写集成测试 |
| client.py | 调用方多 | 保持公共接口不变 |

### 回滚策略

每个重构都在独立分支进行，如果出现问题：
1. 停止当前重构
2. 回滚到 master
3. 分析问题原因
4. 调整重构策略

### 质量门禁

每次重构必须满足：
- [ ] 所有测试通过
- [ ] 覆盖率 ≥ 80%
- [ ] Ruff 检查通过
- [ ] MyPy 检查通过
- [ ] 代码审查通过

---

## 预期收益

| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| 总代码行数 | ~5,500 | ~4,000 | -27% |
| 平均文件行数 | 450 | 150 | -67% |
| 模块数量 | 11 | 26 | +136% |
| 测试覆盖率 | 85% | 90%+ | +5% |
| 代码重复率 | 高 | 低 | 显著降低 |

---

## 附录: 设计模式参考

### 策略模式 (pdf_renderer.py)
用于处理不同类型的 Markdown 元素，每种元素有独立的处理器。

### Repository 模式 (duckdb_manager.py)
用于分离数据访问逻辑，每种实体有独立的 Repository。

### 组合模式 (client.py)
用于组合多个小组件构建复杂的 API 客户端。

### 装饰器模式 (storage_commands.py)
用于提取公共的错误处理和参数解析逻辑。
