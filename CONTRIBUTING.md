# 贡献指南

感谢您对 Diting 项目的关注!本文档介绍如何为项目做出贡献。

## 目录

- [分支管理策略](#分支管理策略)
- [开发流程](#开发流程)
- [分支命名规范](#分支命名规范)
- [提交信息规范](#提交信息规范)
- [代码质量要求](#代码质量要求)
- [Pull Request 流程](#pull-request-流程)

---

## 分支管理策略

Diting 项目采用 **GitHub Flow** 分支管理策略。

### 核心原则

1. **Master 分支始终可部署**: Master 分支上的代码始终处于可运行状态
2. **功能分支开发**: 所有新功能和修复都在独立分支上进行
3. **Pull Request 审查**: 通过 PR 进行代码审查和质量检查
4. **持续集成**: 每个 PR 自动运行测试和代码质量检查
5. **快速合并**: 功能完成后尽快合并,避免长期分支

### 为什么选择 GitHub Flow?

- ✅ 简单直观,6步标准流程
- ✅ 适合单人/小团队快速迭代
- ✅ GitHub 原生支持,工具链完善
- ✅ 无复杂的环境分支管理

---

## 开发流程

### 标准功能开发流程(6步)

#### 1. 从 master 创建功能分支

```bash
# 确保本地 master 分支是最新的
git checkout master
git pull origin master

# 创建功能分支(使用规范命名)
git checkout -b 003-wechat-notification-webhook
```

#### 2. 本地开发和提交

```bash
# 频繁提交小改动
git add src/diting/endpoints/wechat/webhook_app.py
git commit -m "feat(webhook): add FastAPI webhook app skeleton"

git add tests/unit/endpoints/wechat/test_webhook_handler.py
git commit -m "test(webhook): add webhook handler unit tests"

git add src/diting/endpoints/wechat/webhook_handler.py
git commit -m "feat(webhook): implement webhook message handler"
```

**提示**: 遵循 [Conventional Commits](docs/workflow/commit-convention.md) 规范

#### 3. 本地测试验证

```bash
# 运行所有测试
pytest tests/ -v --cov=src

# 代码格式检查
ruff check . --fix

# 类型检查
mypy src/

# 确保覆盖率 ≥ 80%
coverage report --fail-under=80
```

#### 4. 推送功能分支

```bash
git push origin 003-wechat-notification-webhook
```

#### 5. 创建 Pull Request

1. 访问 GitHub 仓库页面
2. 点击 "Compare & pull request"
3. 填写 PR 模板内容:
   - 功能描述
   - 关联文档
   - 测试检查清单
   - 宪章符合性检查
4. 提交 PR

#### 6. 合并到 Master

- 等待 CI 自动测试通过(必须)
- 自我审查代码(推荐)
- 使用 **"Squash and merge"** 合并
- 合并后自动删除功能分支

```bash
# 本地清理
git checkout master
git pull origin master
git branch -d 003-wechat-notification-webhook
```

---

### 热修复流程

紧急 Bug 修复使用相同流程,但可以加快速度:

```bash
# 1. 创建热修复分支
git checkout master
git pull origin master
git checkout -b hotfix/webhook-crash-on-invalid-json

# 2. 快速修复
git add src/diting/endpoints/wechat/webhook_handler.py
git commit -m "fix(webhook): handle invalid JSON gracefully"

git add tests/unit/endpoints/wechat/test_webhook_handler.py
git commit -m "test(webhook): add test for invalid JSON handling"

# 3. 推送并创建紧急 PR
git push origin hotfix/webhook-crash-on-invalid-json

# 4. PR 标题: fix: critical crash on invalid webhook JSON
# 标记为 "priority: high"

# 5. 快速合并(可跳过长时间审查)
# Squash and merge → 立即部署验证
```

---

### 版本发布流程

```bash
# 1. 确保 master 分支稳定
git checkout master
git pull origin master
pytest tests/ -v --cov=src

# 2. 创建版本标签
git tag -a v0.2.0 -m "Release v0.2.0: WeChat webhook service

Features:
- Implement webhook message receiver
- Add structured logging for all messages
- Support concurrent message processing

Closes #3"

# 3. 推送标签
git push origin v0.2.0

# 4. 在 GitHub 创建 Release
# - 标题: v0.2.0 - WeChat Webhook Service
# - 描述: 引用 CHANGELOG.md
# - 附上构建产物(如果有)
```

---

## 分支命名规范

### 功能分支

**格式**: `{spec-id}-{feature-name}`

**示例**:
```
003-wechat-notification-webhook
004-knowledge-graph-core
005-llm-claude-integration
```

**说明**: 使用规范编号作为前缀,便于追溯设计文档

### 热修复分支

**格式**: `hotfix/{issue-description}`

**示例**:
```
hotfix/webhook-crash-on-invalid-json
hotfix/memory-leak-in-logger
hotfix/api-timeout-error
```

**说明**: 使用 `hotfix/` 前缀标识紧急修复

### 实验性分支(可选)

**格式**: `experiment/{feature-name}`

**示例**:
```
experiment/llm-claude-integration
experiment/vector-db-evaluation
experiment/new-parser-algorithm
```

**说明**:
- 用于探索性开发和技术验证
- 可以不创建 PR,直接在本地测试
- 验证成功后可以 rebase 到 master 或重新实现

---

## 提交信息规范

Diting 项目采用 [Conventional Commits](https://www.conventionalcommits.org/) 规范。

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(webhook): implement message handler` |
| `fix` | Bug 修复 | `fix(wechat): handle API timeout gracefully` |
| `docs` | 文档更新 | `docs: update quickstart guide` |
| `test` | 测试代码 | `test(webhook): add integration tests` |
| `refactor` | 代码重构 | `refactor(logger): extract log formatter` |
| `perf` | 性能优化 | `perf(parser): optimize JSON parsing` |
| `chore` | 构建工具/依赖更新 | `chore: upgrade FastAPI to 0.104.1` |
| `style` | 代码格式(不影响逻辑) | `style: fix ruff formatting issues` |
| `ci` | CI 配置更新 | `ci: add codecov integration` |

### Scope 范围(可选)

| Scope | 说明 |
|-------|------|
| `wechat` | 微信端点模块 |
| `webhook` | Webhook 服务 |
| `kg` | 知识图谱模块 |
| `llm` | LLM 分析模块 |
| `cli` | 命令行工具 |
| `config` | 配置管理 |

### 示例

```bash
# 好的提交信息
git commit -m "feat(webhook): implement message handler with retry logic"
git commit -m "fix(wechat): handle timeout in API client gracefully"
git commit -m "docs: update quickstart guide for webhook setup"
git commit -m "test(webhook): add integration tests for FastAPI app"

# 不推荐的提交信息
git commit -m "update code"          # 太模糊
git commit -m "fix bug"              # 缺少具体信息
git commit -m "WIP"                  # 不完整的提交
```

详细规范请参考 [Commit Convention](docs/workflow/commit-convention.md)。

---

## 代码质量要求

### 必须通过的检查

所有 PR 必须通过以下检查才能合并:

#### 1. Ruff 代码格式检查

```bash
# 检查代码风格
ruff check .

# 自动修复
ruff check . --fix

# 检查格式化
ruff format --check .

# 自动格式化
ruff format .
```

#### 2. Mypy 类型检查

```bash
mypy src/
```

**说明**: 类型检查警告不会阻塞 PR,但应尽量修复

#### 3. Pytest 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行契约测试
pytest tests/contract/ -v
```

#### 4. 测试覆盖率

```bash
# 生成覆盖率报告
pytest --cov=src --cov-report=term --cov-report=html

# 检查覆盖率阈值(必须 ≥ 80%)
coverage report --fail-under=80
```

### CI 自动化

每个 PR 会自动运行 `.github/workflows/ci.yml` 中定义的检查:

- ✅ Ruff linting
- ✅ Ruff formatting
- ✅ Mypy type checking
- ✅ Pytest all tests
- ✅ Coverage ≥ 80%

**PR 必须通过所有 CI 检查才能合并。**

---

## Pull Request 流程

### 创建 PR

1. **推送功能分支** 到 GitHub
2. **填写 PR 模板** (自动加载 `.github/pull_request_template.md`)
   - 功能描述
   - 关联文档
   - 测试检查清单
   - 宪章符合性检查
3. **添加标签** (可选):
   - `enhancement`: 新功能
   - `bug`: Bug 修复
   - `documentation`: 文档更新
   - `priority: high`: 高优先级
4. **请求审查** (如果是团队协作)

### PR 审查标准

审查时关注以下方面:

#### 代码质量
- [ ] 代码可读性好,命名清晰
- [ ] 无明显性能问题
- [ ] 无安全漏洞(SQL 注入、XSS 等)
- [ ] 遵循项目编码规范

#### 测试充分性
- [ ] 新功能有对应测试
- [ ] Bug 修复有回归测试
- [ ] 覆盖率 ≥ 80%
- [ ] 测试用例有意义

#### 宪章符合性
- [ ] 符合 Privacy First 原则
- [ ] 符合 Endpoint Modularity 原则
- [ ] 符合 Observability & Testability 原则

#### 文档完整性
- [ ] 公共 API 有文档字符串
- [ ] 复杂逻辑有注释说明
- [ ] README/文档已更新(如需要)

### 合并策略

**推荐使用 "Squash and merge"**:

- ✅ 保持 master 历史简洁清晰
- ✅ 一个 PR 合并为一个 commit
- ✅ 便于回滚和 cherry-pick
- ✅ PR 描述成为 commit message

**合并后自动删除功能分支**。

---

## 项目宪章

Diting 项目遵循以下核心原则(详见 `.specify/memory/constitution.md`):

### I. Privacy First
- ✅ 本地优先存储
- ✅ 端到端加密
- ✅ 最小权限原则
- ✅ 数据隔离
- ✅ 可撤销性
- ✅ 审计日志

### II. Endpoint Modularity
- ✅ 独立部署能力
- ✅ 统一适配器接口
- ✅ 容错隔离
- ✅ 可扩展性
- ✅ 插件化设计

### III. Knowledge Graph Core
- ✅ 实体提取
- ✅ 关系推理
- ✅ 时序追踪
- ✅ 跨端点融合

### IV. LLM-Powered Insights
- ✅ 上下文感知
- ✅ 模式识别
- ✅ 趋势分析
- ✅ 主动建议

### V. Observability & Testability
- ✅ 结构化日志
- ✅ 性能监控
- ✅ 错误追踪
- ✅ ≥ 80% 测试覆盖率
- ✅ 本地调试能力
- ✅ 数据模拟

---

## 常见问题

### Q: 我应该何时创建 PR?

A: 功能开发完成并通过本地测试后即可创建 PR。不要等到"完美"才提交,尽早创建 PR 可以获得反馈。

### Q: PR 应该包含多少个 commit?

A: 在功能分支上可以频繁提交小改动,PR 合并时会使用 "Squash and merge" 压缩为单个 commit。

### Q: 如果 CI 测试失败怎么办?

A: 查看 GitHub Actions 日志,修复问题后推送新的 commit,CI 会自动重新运行。

### Q: 我可以直接推送到 master 吗?

A: ❌ 不可以。Master 分支已配置保护规则,必须通过 PR 才能合并。

### Q: 实验性功能是否需要创建 PR?

A: 取决于情况。如果只是技术验证,可以在 `experiment/*` 分支上本地测试。如果要合并到 master,必须创建 PR。

### Q: 如何回滚已合并的 PR?

A: 使用 `git revert` 命令:

```bash
git checkout master
git pull origin master
git revert <commit-hash>
git push origin master
```

### Q: 忘记了某个功能分支,如何清理?

A: 定期清理已合并的本地分支:

```bash
# 查看已合并的分支
git branch --merged master

# 删除已合并的分支
git branch -d <branch-name>

# 删除远程已删除但本地还在的分支
git fetch --prune
```

---

## 参考资源

- [GitHub Flow Guide](https://githubflow.github.io/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Diting GitHub Flow Workflow](docs/workflow/github-flow.md)
- [Diting Commit Convention](docs/workflow/commit-convention.md)

---

## 获取帮助

如果您在贡献过程中遇到问题:

1. 查看本文档和相关文档
2. 搜索 [GitHub Issues](https://github.com/sqrtqiezi/diting/issues)
3. 创建新的 Issue 提问

感谢您的贡献!🎉
