# Diting (谛听)

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](https://pytest.org/)

个人信息助理项目 - 从多个端点(微信/飞书/邮箱)收集个人隐私数据,构建个人知识库,并通过 LLM 分析生成洞察。

## 特性

- 🔒 **隐私优先**: 本地存储,端到端加密,最小权限
- 🔌 **端点模块化**: 独立的数据源适配器(微信/飞书/邮箱)
- 🕸️ **知识图谱**: 实体提取、关系建模、语义搜索
- 🤖 **LLM 驱动**: AI 分析生成可操作洞察
- 🧪 **可观测可测试**: 完整的测试覆盖率和结构化日志

## 环境设置

### 快速开始

新开发人员可在 **15 分钟**内完成环境配置:

1. **克隆仓库**
   ```bash
   git clone https://github.com/diting/diting.git
   cd diting
   ```

2. **按照环境设置指南操作**

   查看详细的分步指南:
   📖 **[环境设置快速开始](specs/002-python-dev-setup/quickstart.md)**

   指南包含:
   - Python 3.12 安装(使用 pyenv)
   - uv 依赖管理工具安装
   - 虚拟环境创建和激活
   - 开发依赖安装
   - Pre-commit 钩子配置
   - IDE(VS Code/PyCharm)配置
   - 验证检查清单
   - 常见问题排查

3. **验证环境**
   ```bash
   python --version  # 应显示 Python 3.12.x
   pytest tests/ -v  # 运行测试
   ```

### 技术栈

- **语言**: Python 3.12
- **依赖管理**: uv
- **代码质量**: Ruff (格式化 + linting), Mypy (类型检查)
- **测试框架**: Pytest + pytest-cov
- **Pre-commit**: 自动化代码质量检查
- **IDE**: VS Code / PyCharm

## 项目结构

```
diting/
├── specs/                  # 功能规格和设计文档
├── src/                    # 源代码(后续添加)
├── tests/                  # 测试代码
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   └── contract/          # 契约测试
├── docs/                   # 项目文档
├── pyproject.toml         # 项目配置
├── .python-version        # Python 版本固定
└── .pre-commit-config.yaml # Pre-commit 钩子配置
```

## 开发工作流

### 代码质量检查

```bash
# 格式化代码
ruff format .

# Linting 检查
ruff check . --fix

# 类型检查
mypy src/

# 运行所有 pre-commit 检查
pre-commit run --all-files
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html
open htmlcov/index.html  # 查看详细报告

# 运行特定测试
pytest tests/unit/test_example.py -v
```

### 提交代码

Pre-commit 钩子会在提交前自动运行代码质量检查:

```bash
git add .
git commit -m "feat: your feature description"
# Pre-commit 自动运行 ruff format, ruff check, mypy
```

## 贡献

欢迎贡献!请遵循以下步骤:

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

所有代码必须:
- ✅ 通过 Ruff 格式化和 linting
- ✅ 通过 Mypy 类型检查
- ✅ 包含单元测试(覆盖率 ≥ 80%)
- ✅ 通过所有现有测试

## 宪章

Diting 项目遵循严格的[宪章](.specify/memory/constitution.md),定义了 5 个核心原则:

1. **Privacy First** (非协商): 本地存储,端到端加密,最小权限
2. **Endpoint Modularity** (非协商): 独立的端点适配器
3. **Knowledge Graph Core**: 实体提取和关系建模
4. **LLM-Powered Insights**: AI 驱动的洞察生成
5. **Observability & Testability**: 可观测和可测试

## 许可证

MIT License - 详见 LICENSE 文件

## 联系方式

- 项目主页: https://github.com/diting/diting
- Issue 追踪: https://github.com/diting/diting/issues
- 文档: https://github.com/diting/diting/tree/main/docs

---

**版本**: 0.1.0
**最后更新**: 2025-11-01
