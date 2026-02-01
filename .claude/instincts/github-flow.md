---
id: diting-github-flow
trigger: "when making code changes"
confidence: 0.95
domain: git
source: local-repo-analysis
analyzed_commits: 55
---

# 严格遵循 GitHub Flow

## 触发条件
当需要修改代码时

## 行动
**绝对禁止**在 master 分支上直接开发！

### 正确流程
1. 从 master 创建功能分支:
   ```bash
   git checkout master
   git pull origin master
   git checkout -b {NNN}-{feature-name}
   ```

2. 在功能分支上开发和提交

3. 推送并创建 PR:
   ```bash
   git push origin {NNN}-{feature-name}
   ```

4. 通过 GitHub PR 进行 Squash and merge

### 禁止行为
- ❌ 在 master 分支上创建/修改文件
- ❌ 在 master 分支上执行 `git commit`
- ❌ 执行 `git push origin master`
- ❌ 直接合并到 master

## 证据
- 项目 CLAUDE.md 明确规定此规范
- 所有功能都通过 PR 合并
- 有专门的 GitHub Flow Guard 机制
