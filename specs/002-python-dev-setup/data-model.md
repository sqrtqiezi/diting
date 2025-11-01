# Data Model: Python 开发环境配置实体

**Feature**: Python 开发环境标准化配置
**Phase**: Phase 1 - Design
**Date**: 2025-11-01

## 概述

本文档定义 Python 开发环境配置的核心实体模型。由于此功能是基础设施配置,这些实体主要是**配置对象**而非业务领域对象,通过声明式配置文件(pyproject.toml, YAML, JSON)定义。

## 实体模型图

```
┌─────────────────────────────────────────────────────────────┐
│                    Python Environment                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  - python_version: str (3.12)                        │   │
│  │  - virtual_env_path: Path (.venv)                    │   │
│  │  - lock_file: Path (uv.lock)                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ contains
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Dependency Specification                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  - runtime_dependencies: List[Dependency]            │   │
│  │  - dev_dependencies: List[Dependency]                │   │
│  │  - version_constraints: Dict[str, str]               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ governed by
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Code Quality Rules                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  RuffConfig:                                         │   │
│  │    - line_length: int (100)                          │   │
│  │    - target_version: str (py312)                     │   │
│  │    - formatting_rules: FormattingRules               │   │
│  │    - linting_rules: LintingRules                     │   │
│  │                                                       │   │
│  │  MypyConfig:                                         │   │
│  │    - strict_mode: bool                               │   │
│  │    - check_untyped_defs: bool                        │   │
│  │    - ignore_missing_imports: bool                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ validated by
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Test Configuration                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PytestConfig:                                       │   │
│  │    - test_paths: List[Path]                          │   │
│  │    - test_pattern: str (test_*.py)                   │   │
│  │    - output_verbosity: str (verbose)                 │   │
│  │                                                       │   │
│  │  CoverageConfig:                                     │   │
│  │    - min_coverage: int (80)                          │   │
│  │    - exclude_paths: List[str]                        │   │
│  │    - report_formats: List[str] (term, html)          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ integrated into
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      IDE Settings                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  VSCodeSettings:                                     │   │
│  │    - interpreter_path: Path (.venv/bin/python)       │   │
│  │    - formatter: str (ruff)                           │   │
│  │    - linter: str (ruff)                              │   │
│  │    - type_checker: str (mypy)                        │   │
│  │    - format_on_save: bool (true)                     │   │
│  │    - recommended_extensions: List[str]               │   │
│  │    - debug_configuration: LaunchConfig               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 实体详细定义

### 1. Python Environment (Python 环境)

**描述**: 定义项目使用的 Python 版本和虚拟环境配置。

**属性**:

| 属性名 | 类型 | 必需 | 默认值 | 描述 |
|-------|------|------|--------|------|
| `python_version` | `str` | ✅ | `"3.12"` | 项目 Python 版本,写入 .python-version |
| `virtual_env_path` | `Path` | ✅ | `.venv` | 虚拟环境目录路径 |
| `lock_file` | `Path` | ✅ | `uv.lock` | uv 生成的依赖锁文件 |
| `python_executable` | `Path` | 计算 | `.venv/bin/python` | 虚拟环境 Python 可执行文件路径(macOS/Linux) |

**生命周期**:
1. **创建**: 开发人员运行 `uv venv` 创建虚拟环境
2. **激活**: 运行 `source .venv/bin/activate` (macOS/Linux) 或 `.venv\Scripts\activate` (Windows)
3. **验证**: 运行 `python --version` 确认版本为 3.12
4. **销毁**: 删除 `.venv` 目录重建环境

**约束**:
- Python 版本必须为 3.12.x
- 虚拟环境路径不得纳入 Git 版本控制(.gitignore)
- 锁文件必须纳入版本控制,确保依赖一致性

**配置文件映射**:
- `.python-version`: 存储 `python_version`
- `pyproject.toml` `[project]` `requires-python`: 存储版本约束

**示例**:
```toml
# pyproject.toml
[project]
requires-python = ">=3.12,<3.13"
```

```
# .python-version
3.12
```

---

### 2. Dependency Specification (依赖规范)

**描述**: 定义项目运行时和开发时所需的 Python 包依赖。

**属性**:

| 属性名 | 类型 | 必需 | 默认值 | 描述 |
|-------|------|------|--------|------|
| `runtime_dependencies` | `List[Dependency]` | ❌ | `[]` | 运行时依赖(目前为空,后续功能添加) |
| `dev_dependencies` | `List[Dependency]` | ✅ | 见下表 | 开发依赖(工具链) |
| `version_constraints` | `Dict[str, str]` | ✅ | 精确版本 | 每个依赖的版本约束策略 |

**Dependency 子实体**:

| 属性名 | 类型 | 描述 | 示例 |
|-------|------|------|------|
| `name` | `str` | 包名 | `"ruff"` |
| `version` | `str` | 版本约束 | `"^0.1.0"` (语义化), `">=0.1.0,<0.2.0"` (范围) |
| `optional` | `bool` | 是否可选依赖 | `false` |
| `extras` | `List[str]` | 安装额外组件 | `["dev"]` |

**开发依赖清单**:

| 包名 | 版本约束 | 用途 |
|------|---------|------|
| `ruff` | `^0.1.0` | 代码格式化和 linting |
| `mypy` | `^1.7.0` | 类型检查 |
| `pytest` | `^7.4.0` | 测试框架 |
| `pytest-cov` | `^4.1.0` | 测试覆盖率 |
| `pre-commit` | `^3.5.0` | Pre-commit 钩子管理 |

**约束**:
- 开发依赖必须锁定主版本(避免破坏性更新)
- 版本约束策略: 使用 `>=x.y.z,<x+1.0.0` 范围约束
- 所有依赖必须通过 `uv.lock` 锁定精确版本

**配置文件映射**:
```toml
# pyproject.toml
[project]
dependencies = []  # 运行时依赖(目前为空)

[project.optional-dependencies]
dev = [
    "ruff>=0.1.0,<0.2.0",
    "mypy>=1.7.0,<2.0.0",
    "pytest>=7.4.0,<8.0.0",
    "pytest-cov>=4.1.0,<5.0.0",
    "pre-commit>=3.5.0,<4.0.0",
]
```

**安装命令**:
```bash
# 安装开发依赖
uv pip install -e ".[dev]"
```

---

### 3. Code Quality Rules (代码质量规则)

**描述**: 定义代码格式化、linting 和类型检查的具体规则。

#### 3.1 RuffConfig (Ruff 配置)

**属性**:

| 属性名 | 类型 | 必需 | 默认值 | 描述 |
|-------|------|------|--------|------|
| `line_length` | `int` | ✅ | `100` | 最大行长度 |
| `target_version` | `str` | ✅ | `"py312"` | 目标 Python 版本 |
| `indent_width` | `int` | ✅ | `4` | 缩进宽度(空格数) |
| `quote_style` | `str` | ✅ | `"double"` | 引号风格(double/single) |
| `formatting_rules` | `FormattingRules` | ✅ | 见下 | 格式化规则 |
| `linting_rules` | `LintingRules` | ✅ | 见下 | Linting 规则集 |
| `exclude_paths` | `List[str]` | ✅ | 见下 | 排除路径 |

**FormattingRules 子实体**:

| 属性名 | 类型 | 默认值 | 描述 |
|-------|------|--------|------|
| `skip_magic_trailing_comma` | `bool` | `false` | 是否跳过魔术尾随逗号 |
| `line_ending` | `str` | `"auto"` | 行尾符(auto/lf/crlf) |

**LintingRules 子实体**:

| 规则集 | 代码 | 描述 | 启用 |
|-------|------|------|------|
| Pyflakes | `F` | 逻辑错误检测 | ✅ |
| pycodestyle | `E`, `W` | PEP 8 风格 | ✅ |
| isort | `I` | Import 排序 | ✅ |
| pydocstyle | `D` | Docstring 风格 | ❌ (初期) |
| pyupgrade | `UP` | Python 版本升级建议 | ✅ |
| flake8-bugbear | `B` | 常见 bug 检测 | ✅ |
| flake8-simplify | `SIM` | 代码简化建议 | ✅ |

**配置文件映射**:
```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py312"
indent-width = 4

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "auto"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = []
exclude = [
    ".venv",
    "__pycache__",
    "*.egg-info",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
]
```

#### 3.2 MypyConfig (Mypy 配置)

**属性**:

| 属性名 | 类型 | 必需 | 默认值 | 描述 |
|-------|------|------|--------|------|
| `python_version` | `str` | ✅ | `"3.12"` | 检查的 Python 版本 |
| `strict_mode` | `bool` | ✅ | `false` | 是否启用严格模式(初期 false) |
| `warn_return_any` | `bool` | ✅ | `true` | 警告返回 Any 类型 |
| `warn_unused_configs` | `bool` | ✅ | `true` | 警告未使用的配置 |
| `disallow_untyped_defs` | `bool` | ❌ | `false` | 禁止无类型注解函数(逐步启用) |
| `ignore_missing_imports` | `bool` | ✅ | `true` | 忽略无 stub 的第三方库 |
| `exclude_paths` | `List[str]` | ✅ | `["tests/"]` | 排除路径 |

**配置文件映射**:
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
exclude = ["tests/"]

# 未来逐步启用:
# strict = true
# disallow_untyped_defs = true
```

---

### 4. Test Configuration (测试配置)

**描述**: 定义测试框架和覆盖率的配置。

#### 4.1 PytestConfig (Pytest 配置)

**属性**:

| 属性名 | 类型 | 必需 | 默认值 | 描述 |
|-------|------|------|--------|------|
| `test_paths` | `List[Path]` | ✅ | `["tests"]` | 测试目录路径 |
| `test_file_pattern` | `str` | ✅ | `"test_*.py"` | 测试文件命名模式 |
| `test_class_pattern` | `str` | ✅ | `"Test*"` | 测试类命名模式 |
| `test_function_pattern` | `str` | ✅ | `"test_*"` | 测试函数命名模式 |
| `output_verbosity` | `str` | ✅ | `"verbose"` | 输出详细度(verbose/-v) |
| `show_capture` | `str` | ✅ | `"no"` | 显示 print 输出(no/all) |
| `addopts` | `List[str]` | ✅ | 见下 | 额外选项 |

**addopts 额外选项**:
- `-v`: 详细输出
- `--strict-markers`: 严格标记检查
- `--tb=short`: 简短 traceback
- `--cov=src`: 覆盖率检查(指向 src/ 目录)
- `--cov-report=term-missing`: 终端显示未覆盖行
- `--cov-report=html`: 生成 HTML 报告

**配置文件映射**:
```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html",
]
```

#### 4.2 CoverageConfig (覆盖率配置)

**属性**:

| 属性名 | 类型 | 必需 | 默认值 | 描述 |
|-------|------|------|--------|------|
| `source_paths` | `List[str]` | ✅ | `["src"]` | 覆盖率检查的源码路径 |
| `min_coverage` | `int` | ✅ | `80` | 最低覆盖率百分比 |
| `exclude_lines` | `List[str]` | ✅ | 见下 | 排除覆盖率的代码行模式 |
| `omit_paths` | `List[str]` | ✅ | 见下 | 忽略的文件路径 |
| `report_formats` | `List[str]` | ✅ | `["term", "html"]` | 报告格式 |

**exclude_lines 排除模式**:
- `pragma: no cover`: 手动标记排除
- `def __repr__`: `__repr__` 方法
- `if TYPE_CHECKING:`: 类型检查块
- `raise NotImplementedError`: 抽象方法

**omit_paths 忽略路径**:
- `tests/*`: 测试代码本身
- `*/__init__.py`: 空 init 文件
- `.venv/*`: 虚拟环境

**配置文件映射**:
```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = [
    "tests/*",
    "*/__init__.py",
    ".venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
fail_under = 80

[tool.coverage.html]
directory = "htmlcov"
```

---

### 5. IDE Settings (IDE 设置)

**描述**: VS Code 和 PyCharm IDE 的项目配置。

#### 5.1 VSCodeSettings (VS Code 配置)

**属性**:

| 属性名 | 类型 | 必需 | 默认值 | 描述 |
|-------|------|------|--------|------|
| `interpreter_path` | `Path` | ✅ | `".venv/bin/python"` | Python 解释器路径 |
| `formatter` | `str` | ✅ | `"ruff"` | 代码格式化工具 |
| `linter` | `str` | ✅ | `"ruff"` | Linting 工具 |
| `type_checker` | `str` | ✅ | `"mypy"` | 类型检查工具 |
| `format_on_save` | `bool` | ✅ | `true` | 保存时自动格式化 |
| `organize_imports_on_save` | `bool` | ✅ | `true` | 保存时整理 imports |
| `test_framework` | `str` | ✅ | `"pytest"` | 测试框架 |
| `recommended_extensions` | `List[str]` | ✅ | 见下 | 推荐插件 |

**推荐插件列表**:
- `ms-python.python`: Python 官方插件
- `ms-python.vscode-pylance`: Pylance(语言服务器)
- `charliermarsh.ruff`: Ruff 官方插件
- `ms-python.mypy-type-checker`: Mypy 插件

**配置文件映射**:
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "mypy-type-checker.importStrategy": "fromEnvironment"
}
```

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker"
  ]
}
```

#### 5.2 LaunchConfig (调试配置)

**属性**:

| 属性名 | 类型 | 必需 | 默认值 | 描述 |
|-------|------|------|--------|------|
| `type` | `str` | ✅ | `"python"` | 调试器类型 |
| `request` | `str` | ✅ | `"launch"` | 请求类型 |
| `program` | `str` | ✅ | `"${file}"` | 运行的程序文件 |
| `console` | `str` | ✅ | `"integratedTerminal"` | 控制台类型 |
| `justMyCode` | `bool` | ✅ | `true` | 仅调试用户代码 |

**配置文件映射**:
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "justMyCode": true
    },
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v"],
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

---

## 实体关系总结

```
Python Environment
  ├── contains → Dependency Specification
  │                 ├── runtime_dependencies: List[Dependency]
  │                 └── dev_dependencies: List[Dependency]
  │
  ├── governed by → Code Quality Rules
  │                    ├── RuffConfig (formatting + linting)
  │                    └── MypyConfig (type checking)
  │
  ├── validated by → Test Configuration
  │                     ├── PytestConfig (test discovery)
  │                     └── CoverageConfig (coverage rules)
  │
  └── integrated into → IDE Settings
                          ├── VSCodeSettings (editor config)
                          └── LaunchConfig (debug config)
```

---

## 配置文件映射总览

| 实体 | 配置文件 | 配置节 |
|------|---------|--------|
| Python Environment | `.python-version`, `pyproject.toml` | `[project]` `requires-python` |
| Dependency Specification | `pyproject.toml` | `[project.dependencies]`, `[project.optional-dependencies]` |
| RuffConfig | `pyproject.toml` | `[tool.ruff]`, `[tool.ruff.format]`, `[tool.ruff.lint]` |
| MypyConfig | `pyproject.toml` | `[tool.mypy]` |
| PytestConfig | `pyproject.toml` | `[tool.pytest.ini_options]` |
| CoverageConfig | `pyproject.toml` | `[tool.coverage.run]`, `[tool.coverage.report]` |
| VSCodeSettings | `.vscode/settings.json` | 顶层 JSON 对象 |
| LaunchConfig | `.vscode/launch.json` | `configurations[]` 数组 |

---

## 验证规则

### 1. Python Environment 验证
- ✅ Python 版本必须为 3.12.x
- ✅ `.venv` 目录必须存在且包含 `bin/python` (macOS/Linux) 或 `Scripts/python.exe` (Windows)
- ✅ `uv.lock` 必须存在且与 `pyproject.toml` 依赖一致

### 2. Dependency Specification 验证
- ✅ 所有开发依赖必须在 `[project.optional-dependencies.dev]` 中声明
- ✅ 版本约束必须使用范围约束(如 `>=x.y.z,<x+1.0.0`)
- ✅ `uv pip list` 输出必须与 `uv.lock` 一致

### 3. Code Quality Rules 验证
- ✅ Ruff 配置必须指定 `target-version = "py312"`
- ✅ Ruff linting 必须启用至少 `E`, `F`, `I` 规则集
- ✅ Mypy 配置必须指定 `python_version = "3.12"`

### 4. Test Configuration 验证
- ✅ `tests/` 目录必须存在
- ✅ Coverage 最低要求必须 ≥ 80%
- ✅ Pytest 必须配置覆盖率报告生成

### 5. IDE Settings 验证
- ✅ `.vscode/settings.json` 必须指向项目虚拟环境
- ✅ 推荐插件列表必须包含 Python 和 Ruff 插件
- ✅ `launch.json` 必须包含 Pytest 调试配置

---

## 下一步行动

1. ✅ 数据模型定义完成
2. ⏭️ 创建 `contracts/` 目录并定义配置文件 JSON Schema
3. ⏭️ 编写 `quickstart.md` 环境设置指南
4. ⏭️ 生成 `tasks.md` 实施任务清单

**完成日期**: 2025-11-01
**下一阶段**: 创建 contracts/ 配置文件模式定义
