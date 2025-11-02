# Diting (谛听)

[![Test](https://github.com/diting/diting/workflows/Test/badge.svg)](https://github.com/diting/diting/actions/workflows/test.yml)
[![Deploy](https://github.com/diting/diting/workflows/Deploy%20to%20Aliyun%20ECS/badge.svg)](https://github.com/diting/diting/actions/workflows/deploy.yml)
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

## CI/CD 和部署

Diting 项目实现了完整的自动化 CI/CD 流程:

### 🧪 自动化测试 (User Story 1)

每次代码推送时,GitHub Actions 自动运行:
- **代码质量检查**: Ruff linter + formatter
- **类型检查**: Mypy 类型验证
- **测试套件**: Pytest with 80% 覆盖率要求
- **覆盖率报告**: 自动生成并上传

### 🚀 自动化部署 (User Story 2)

合并到 master 分支后,自动部署到阿里云 ECS:
- **零停机部署**: 基于符号链接的版本切换
- **健康检查**: 部署后自动验证服务状态
- **自动回滚**: 健康检查失败时回滚到上一个版本
- **版本管理**: 保留最近 3 个版本,自动清理旧版本

### 📊 部署可见性 (User Story 3)

- **状态徽章**: README 顶部显示 workflow 状态
- **部署历史**: GitHub Actions 界面查看详细日志
- **失败通知**: 部署失败时自动创建 GitHub Issue

**相关文档**:
- 📖 [CI/CD 快速上手](specs/005-github-ci-aliyun-deploy/quickstart.md) - 首次部署指南
- 📖 [环境差异说明](docs/ci-cd/environment-differences.md) - 本地/CI/生产环境差异
- 📖 [act 本地 CI 工具](docs/ci-cd/act-setup.md) - 本地复现 CI 环境

## 开发工作流

### 分支管理策略

Diting 项目采用 **GitHub Flow** 分支管理策略:

1. **Master 分支始终可部署** - master 分支上的代码始终处于稳定状态
2. **功能分支开发** - 所有新功能和修复都在独立分支上进行
3. **Pull Request 审查** - 通过 PR 进行代码审查和 CI 验证
4. **快速合并** - 功能完成后尽快合并,避免长期分支

**详细文档**:
- 📖 [贡献指南](CONTRIBUTING.md) - 完整开发流程说明
- 📖 [GitHub Flow 详解](docs/workflow/github-flow.md) - 分支策略详解
- 📖 [Commit 规范](docs/workflow/commit-convention.md) - 提交信息规范

### 开发流程(6步)

```bash
# 1. 从 master 创建功能分支
git checkout master
git pull origin master
git checkout -b 003-your-feature-name

# 2. 本地开发和提交(遵循 Conventional Commits 规范)
git add src/your_changes.py
git commit -m "feat(scope): implement your feature"

# 3. 本地测试验证
pytest tests/ -v --cov=src
ruff check . --fix
mypy src/

# 4. 推送功能分支
git push origin 003-your-feature-name

# 5. 创建 Pull Request
# 访问 GitHub 仓库,填写 PR 模板

# 6. 合并到 Master (CI 通过后)
# 使用 "Squash and merge" → 自动删除功能分支
```

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

# 检查覆盖率阈值(≥ 80%)
coverage report --fail-under=80
```

### 提交信息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范:

```bash
# 格式: <type>(<scope>): <subject>

# 新功能
git commit -m "feat(webhook): implement message retry logic"

# Bug 修复
git commit -m "fix(wechat): handle API timeout gracefully"

# 文档更新
git commit -m "docs: update README installation guide"

# 测试代码
git commit -m "test(webhook): add integration tests"
```

**常用 Type**: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `style`, `ci`

**常用 Scope**: `wechat`, `webhook`, `kg`, `llm`, `cli`, `config`, `logger`

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
