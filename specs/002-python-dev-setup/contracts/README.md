# Configuration Contracts

本目录包含 Python 开发环境配置文件的结构定义(Schema)。

## 文件列表

### 1. pyproject.toml.schema

**定义**: Python 项目统一配置文件结构
**涵盖内容**:
- 项目元数据(`[project]`)
- 依赖规范(`[project.dependencies]`, `[project.optional-dependencies]`)
- Ruff 配置(`[tool.ruff]`, `[tool.ruff.format]`, `[tool.ruff.lint]`)
- Mypy 配置(`[tool.mypy]`)
- Pytest 配置(`[tool.pytest.ini_options]`)
- Coverage 配置(`[tool.coverage.run]`, `[tool.coverage.report]`)
- uv 配置(`[tool.uv]`)

**位置**: 项目根目录 `/pyproject.toml`

---

### 2. pre-commit-config.schema

**定义**: Pre-commit 钩子配置文件结构
**涵盖内容**:
- Global configuration(`fail_fast`, `default_language_version`)
- Repository hooks:
  - Pre-commit official hooks(trailing-whitespace, check-yaml, etc.)
  - Ruff hooks(ruff, ruff-format)
  - Mypy hook

**位置**: 项目根目录 `/.pre-commit-config.yaml`

---

### 3. vscode-settings.schema

**定义**: VS Code IDE 配置文件结构
**涵盖内容**:
- `.vscode/settings.json`:
  - Python 解释器配置
  - 格式化配置(Ruff)
  - Linting 配置(Ruff)
  - 类型检查配置(Mypy)
  - 测试配置(Pytest)
  - 编辑器配置
- `.vscode/extensions.json`:
  - 推荐插件列表
- `.vscode/launch.json`:
  - 调试配置(Python, Pytest)

**位置**: 项目根目录 `.vscode/` 目录

---

## 配置组织策略

### 统一配置文件(推荐)

我们选择 **pyproject.toml 统一配置**策略,将所有 Python 工具配置集中在单一文件中:

**优势**:
- ✅ 符合 PEP 518/621 标准
- ✅ 减少配置文件碎片
- ✅ 集中管理,易于维护
- ✅ 所有工具(Ruff, Mypy, Pytest)完美支持

**例外**:
- `.pre-commit-config.yaml`: Pre-commit 框架要求 YAML 格式
- `.python-version`: pyenv 要求独立文件
- `.vscode/`: IDE 配置,独立目录

### 不需要的单独配置文件

以下配置**不需要**单独文件,已嵌入 `pyproject.toml`:

| 不需要的文件 | 替代方案 | 说明 |
|------------|---------|------|
| `ruff.toml` | `[tool.ruff]` in `pyproject.toml` | Ruff 支持 pyproject.toml 配置 |
| `mypy.ini` | `[tool.mypy]` in `pyproject.toml` | Mypy 支持 pyproject.toml 配置 |
| `pytest.ini` | `[tool.pytest.ini_options]` in `pyproject.toml` | Pytest 支持 pyproject.toml 配置 |
| `setup.py` | `[project]` in `pyproject.toml` | PEP 621 替代 setup.py |
| `requirements.txt` | `[project.dependencies]` in `pyproject.toml` | uv 使用 pyproject.toml |

---

## 使用说明

### 1. 创建配置文件

参考对应的 `.schema` 文件,创建实际配置文件:

```bash
# 1. 创建 pyproject.toml
# 参考: contracts/pyproject.toml.schema
# 复制 Schema Structure 部分到项目根目录

# 2. 创建 .pre-commit-config.yaml
# 参考: contracts/pre-commit-config.schema
# 复制 Schema Structure 部分到项目根目录

# 3. 创建 VS Code 配置
# 参考: contracts/vscode-settings.schema
# 复制各配置文件到 .vscode/ 目录
```

### 2. 验证配置

```bash
# 验证 TOML 语法
python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"

# 验证 YAML 语法
pre-commit validate-config

# 验证 JSON 语法(VS Code settings)
python -m json.tool .vscode/settings.json > /dev/null
```

### 3. 应用配置

```bash
# 安装依赖(应用 pyproject.toml)
uv pip install -e ".[dev]"

# 安装 pre-commit 钩子(应用 .pre-commit-config.yaml)
pre-commit install

# 打开 VS Code(应用 .vscode/ 配置)
code .
```

---

## 配置验证规则

### pyproject.toml 验证

- ✅ `[project]` 节必须包含: `name`, `version`, `requires-python`
- ✅ `requires-python` 必须为 `">=3.12,<3.13"`
- ✅ `[project.optional-dependencies.dev]` 必须包含: ruff, mypy, pytest, pytest-cov, pre-commit
- ✅ `[tool.ruff]` 必须指定 `target-version = "py312"`
- ✅ `[tool.mypy]` 必须指定 `python_version = "3.12"`
- ✅ `[tool.coverage.report]` 必须设置 `fail_under >= 80`

### .pre-commit-config.yaml 验证

- ✅ `repos` 必须包含 Ruff 和 Mypy hooks
- ✅ Ruff hook 必须包含 `--fix` 参数
- ✅ Mypy hook 必须指定 `--config-file=pyproject.toml`
- ✅ 必须包含安全检查 hooks(detect-private-key, check-added-large-files)

### .vscode/settings.json 验证

- ✅ `python.defaultInterpreterPath` 必须指向 `.venv`
- ✅ `[python].editor.defaultFormatter` 必须为 `"charliermarsh.ruff"`
- ✅ `editor.rulers` 必须与 `pyproject.toml` 中 `ruff.line-length` 一致(100)

---

## Constitution 合规性

所有配置文件均符合 Diting Constitution 原则:

### Privacy First (原则 I) - ✅
- 所有工具本地运行,无代码上传外部服务
- 敏感配置(如私有 PyPI token)通过环境变量管理,不纳入版本控制
- Pre-commit hooks 包含私钥检测,防止泄露

### Observability & Testability (原则 V) - ✅
- Pytest 配置支持单元测试、集成测试、契约测试
- Coverage 配置确保测试覆盖率 ≥ 80%
- Pre-commit 记录所有代码质量检查结果

### 无复杂度违规 - ✅
- 统一配置文件,避免配置碎片化
- 工具选择遵循"简单优于复杂"原则
- 无过度工程

---

## 参考资源

- PEP 518: https://peps.python.org/pep-0518/
- PEP 621: https://peps.python.org/pep-0621/
- Ruff Configuration: https://docs.astral.sh/ruff/configuration/
- Mypy Configuration: https://mypy.readthedocs.io/en/stable/config_file.html
- Pytest Configuration: https://docs.pytest.org/en/stable/reference/customize.html
- Pre-commit Configuration: https://pre-commit.com/
- VS Code Python Settings: https://code.visualstudio.com/docs/python/settings-reference

---

**Last Updated**: 2025-11-01
**Schema Version**: 1.0.0
