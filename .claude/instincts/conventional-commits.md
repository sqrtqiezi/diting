---
id: diting-conventional-commits
trigger: "when writing a commit message"
confidence: 0.80
domain: git
source: local-repo-analysis
analyzed_commits: 55
---

# 使用 Conventional Commits 格式

## 触发条件
当需要编写 git commit 消息时

## 行动
使用以下格式编写提交信息：
```
<type>(<scope>): <subject>
```

### Type 选择
- `feat`: 新功能代码
- `fix`: Bug 修复
- `docs`: 文档（spec.md, plan.md, tasks.md, README.md）
- `test`: 测试代码
- `refactor`: 代码重构
- `style`: 代码格式

### Scope 选择
- 功能编号: `003`, `005`, `006`, `035`, `042`
- 模块名: `cli`, `webhook`, `llm`, `deploy`, `report`

## 证据
- 分析了 55 个提交
- 80% 遵循 Conventional Commits 格式
- 示例: `feat(006): implement WeChat message storage with Parquet backend (#30)`
