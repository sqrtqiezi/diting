# Commit 提交信息规范

Diting 项目采用 [Conventional Commits](https://www.conventionalcommits.org/) 规范来编写提交信息。

## 为什么需要规范?

- ✅ **可读性**: 清晰的提交历史,易于理解每个变更的目的
- ✅ **自动化**: 支持自动生成 CHANGELOG
- ✅ **语义化版本**: 根据 commit type 自动确定版本号(major/minor/patch)
- ✅ **过滤查找**: 快速查找特定类型的提交(`git log --grep="^feat"`)
- ✅ **协作效率**: 团队成员快速理解变更内容

---

## 格式规范

### 基本格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 详细说明

#### Type(必填)

提交类型,表明此次变更的性质:

| Type | 说明 | 影响版本 | 示例 |
|------|------|----------|------|
| `feat` | 新功能 | MINOR | `feat(webhook): implement message retry logic` |
| `fix` | Bug 修复 | PATCH | `fix(wechat): handle API timeout gracefully` |
| `docs` | 文档更新 | - | `docs: update README installation guide` |
| `test` | 测试代码 | - | `test(webhook): add integration tests for FastAPI app` |
| `refactor` | 代码重构(不改变功能) | - | `refactor(logger): extract formatter to separate function` |
| `perf` | 性能优化 | PATCH | `perf(parser): optimize JSON parsing with ujson` |
| `chore` | 构建工具/依赖更新 | - | `chore: upgrade FastAPI to 0.104.1` |
| `style` | 代码格式(不影响逻辑) | - | `style: fix ruff formatting issues` |
| `ci` | CI 配置更新 | - | `ci: add codecov integration to GitHub Actions` |
| `revert` | 回滚之前的提交 | - | `revert: revert "feat: add experimental feature"` |

#### Scope(可选)

影响范围,表明此次变更影响的模块:

| Scope | 说明 | 示例 |
|-------|------|------|
| `wechat` | 微信端点模块 | `feat(wechat): add contact sync` |
| `webhook` | Webhook 服务 | `fix(webhook): handle invalid JSON` |
| `kg` | 知识图谱模块 | `feat(kg): implement entity extraction` |
| `llm` | LLM 分析模块 | `feat(llm): integrate Claude API` |
| `cli` | 命令行工具 | `feat(cli): add new serve command` |
| `config` | 配置管理 | `refactor(config): use pydantic-settings` |
| `logger` | 日志系统 | `perf(logger): use rotating file handler` |

**如果无明确 scope,可省略括号**:
```bash
docs: update README
chore: upgrade dependencies
```

#### Subject(必填)

简短描述,不超过 50 字符:

- ✅ 使用动词开头(add, implement, fix, update, remove)
- ✅ 使用祈使句(add feature, not added feature)
- ✅ 首字母小写
- ❌ 结尾不加句号
- ❌ 不要太模糊(update code, fix bug)

**好的 subject**:
```
implement message retry logic
handle API timeout gracefully
update README installation guide
extract formatter to separate function
```

**不好的 subject**:
```
Update code.          # 太模糊 + 有句号
fixed the bug         # 应该用 fix + 缺少具体信息
Added new feature     # 首字母不应大写
WIP                   # 不完整的提交
```

#### Body(可选)

详细描述变更的原因、内容、影响:

- 解释 **为什么** 做这个变更
- 说明 **做了什么**
- 提及 **有什么影响**
- 每行不超过 72 字符

**示例**:
```
feat(webhook): implement message retry logic

微信 API 偶尔会超时导致消息丢失,现在添加重试机制:
- 使用指数退避策略(1s, 2s, 4s, 8s, 16s)
- 最多重试 5 次
- 在日志中记录重试次数和最终结果

这将显著降低消息丢失率,提高系统可靠性。
```

#### Footer(可选)

引用 Issue、标注破坏性变更:

**关联 Issue**:
```
Closes #123
Fixes #456
Refs #789
```

**破坏性变更**:
```
BREAKING CHANGE: API 签名已改变,需要更新调用方代码

之前: client.send_message(content)
现在: client.send_message(content, retry=True)
```

---

## 完整示例

### 示例 1: 新功能(简单)

```bash
git commit -m "feat(webhook): add health check endpoint"
```

### 示例 2: 新功能(详细)

```bash
git commit -m "feat(kg): implement entity extraction from messages

添加基于 spaCy 的实体提取功能:
- 支持提取人名、地名、组织名
- 使用 zh_core_web_sm 中文模型
- 提取结果存储为 Entity 对象

这是知识图谱核心功能的第一步,后续将添加关系推理。

Refs #15"
```

### 示例 3: Bug 修复

```bash
git commit -m "fix(webhook): handle invalid JSON gracefully

之前收到格式错误的 JSON 时会抛出异常导致服务崩溃,
现在改为记录 parse_error 字段并继续处理后续请求。

Fixes #28"
```

### 示例 4: 破坏性变更

```bash
git commit -m "feat(wechat)!: change API client initialization

BREAKING CHANGE: WeChatAPIClient 构造函数签名已改变

之前:
  client = WeChatAPIClient(api_key, api_secret)

现在:
  config = WeChatConfig.load_from_yaml('config/wechat.yaml')
  client = WeChatAPIClient(config)

迁移指南见 docs/migration/v0.2.md

Closes #45"
```

**注意**: 破坏性变更在 type 后加 `!`,例如 `feat!:` 或 `fix(api)!:`

### 示例 5: 回滚提交

```bash
git commit -m "revert: revert \"feat(llm): add Claude API integration\"

This reverts commit abc1234567890.

Claude API 集成导致响应时间增加 2 倍,暂时回滚,
等性能优化完成后再重新引入。"
```

---

## 快速参考

### Commit Type 速查表

```bash
# 新功能
git commit -m "feat(scope): add new feature"

# Bug 修复
git commit -m "fix(scope): resolve specific bug"

# 文档
git commit -m "docs: update documentation"

# 测试
git commit -m "test(scope): add unit tests"

# 重构
git commit -m "refactor(scope): improve code structure"

# 性能
git commit -m "perf(scope): optimize performance"

# 构建工具
git commit -m "chore: update dependencies"

# 代码风格
git commit -m "style: fix formatting"

# CI 配置
git commit -m "ci: add new workflow"
```

### 实际项目示例

```bash
# 微信端点相关
feat(wechat): implement contact synchronization
fix(wechat): handle rate limit with exponential backoff
test(wechat): add API client integration tests

# Webhook 服务相关
feat(webhook): add message deduplication
fix(webhook): prevent memory leak in logger
perf(webhook): optimize JSON parsing with ujson

# 知识图谱相关
feat(kg): implement relationship extraction
refactor(kg): extract entity types to enum
test(kg): add graph traversal unit tests

# 通用
docs: update quickstart guide
chore: upgrade Python to 3.12.6
ci: add coverage reporting to GitHub Actions
```

---

## 工具集成

### Git Commit Template

创建 `.gitmessage` 模板:

```bash
# 在项目根目录
cat > .gitmessage << 'EOF'
# <type>(<scope>): <subject>
#
# <body>
#
# <footer>

# Type: feat, fix, docs, test, refactor, perf, chore, style, ci, revert
# Scope: wechat, webhook, kg, llm, cli, config, logger
# Subject: 不超过 50 字符,使用祈使句,首字母小写,无句号
#
# Body: 详细描述变更原因、内容、影响,每行 < 72 字符
#
# Footer: Closes #123, Fixes #456, Refs #789
#         BREAKING CHANGE: 描述破坏性变更
EOF

# 配置 Git 使用模板
git config commit.template .gitmessage
```

使用:
```bash
git commit  # 会打开编辑器,显示模板
```

### Commitlint(可选)

自动验证提交信息格式:

```bash
# 安装 commitlint
npm install --save-dev @commitlint/cli @commitlint/config-conventional

# 配置 commitlint.config.js
echo "module.exports = {extends: ['@commitlint/config-conventional']}" > commitlint.config.js

# 安装 husky(Git hooks)
npm install --save-dev husky
npx husky install
npx husky add .husky/commit-msg 'npx --no -- commitlint --edit "$1"'
```

现在每次提交都会自动验证格式:
```bash
git commit -m "bad commit message"  # 会被拒绝
git commit -m "feat: good commit"   # 通过
```

---

## 常见问题

### Q: Scope 应该多细?

A: 以项目的主要模块为准。Diting 项目推荐 scope:
- `wechat`, `webhook`, `kg`, `llm`, `cli`, `config`, `logger`

### Q: 一次 commit 修改了多个 scope 怎么办?

A: 优先拆分为多个 commit。如果实在无法拆分,选择主要影响的 scope 或省略 scope。

### Q: 什么时候使用 BREAKING CHANGE?

A: 任何导致用户需要修改代码的变更:
- API 签名改变
- 配置格式改变
- 删除已有功能
- 行为逻辑改变

### Q: WIP commit 怎么处理?

A: 不推荐 WIP commit。如果必须:
```bash
# 本地开发时
git commit -m "WIP: experiment with new parser"

# PR 前使用 rebase 整理
git rebase -i HEAD~5
# 将 WIP commits 压缩(squash)为有意义的提交
```

### Q: 如何修改最近的 commit message?

A: 使用 `git commit --amend`:
```bash
# 修改最近一次提交的 message
git commit --amend -m "feat(webhook): correct message"

# 修改更早的提交
git rebase -i HEAD~3
# 将要修改的 commit 标记为 'reword'
```

---

## 参考资源

- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Angular Commit Message Guidelines](https://github.com/angular/angular/blob/master/CONTRIBUTING.md#commit)
- [Semantic Versioning](https://semver.org/)
- [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)

---

**文档版本**: 1.0.0
**更新日期**: 2025-11-02
**维护者**: Diting Development Team
