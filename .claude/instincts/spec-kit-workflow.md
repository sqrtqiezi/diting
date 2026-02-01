---
id: diting-spec-kit-workflow
trigger: "when starting a new feature"
confidence: 0.85
domain: workflow
source: local-repo-analysis
analyzed_commits: 55
---

# 使用 Spec-Kit 驱动开发

## 触发条件
当开始开发新功能时

## 行动
1. 创建功能分支: `git checkout -b {NNN}-{feature-name}`
2. 执行 spec-kit 工作流:
   - `/speckit.specify` → 编写功能规范
   - `/speckit.plan` → 制定实现计划
   - `/speckit.tasks` → 分解任务
   - `/speckit.implement` → 实现功能

3. 在 `specs/{NNN}-{feature-name}/` 目录下创建:
   - `spec.md` - 功能规范（用户故事、验收标准）
   - `plan.md` - 实现计划
   - `tasks.md` - 任务分解
   - `quickstart.md` - 快速开始指南

## 证据
- 项目中有 6 个功能规范目录
- 所有功能都遵循此工作流
- 示例: `specs/006-wechat-message-storage/`
