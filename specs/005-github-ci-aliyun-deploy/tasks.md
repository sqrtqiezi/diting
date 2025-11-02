# Tasks: GitHub CI/CD 与阿里云 ECS 部署

**Input**: Design documents from `/specs/005-github-ci-aliyun-deploy/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Organization**: Tasks are grouped by user story (P1→P2→P3) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 项目初始化和基础配置

- [X] T001 创建 .github/workflows/ 目录结构
- [X] T002 创建 deploy/ 目录用于部署配置文件
- [X] T003 创建 docs/ci-cd/ 目录用于 CI/CD 文档

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 核心基础设施,必须在任何用户故事之前完成

**⚠️ CRITICAL**: 所有用户故事工作必须等待此阶段完成

- [X] T004 在 src/diting/endpoints/wechat/webhook_app.py 中实现 /health 健康检查端点 (已存在)
- [X] T005 [P] 创建 tests/unit/endpoints/wechat/test_webhook_app_health.py 健康检查单元测试 (已存在)
- [X] T006 [P] 创建 deploy/diting.service systemd 服务配置文件(参考 contracts/systemd-service.service)
- [X] T007 [P] 创建 docs/ci-cd/environment-differences.md 环境差异文档
- [X] T008 [P] 创建 docs/ci-cd/act-setup.md 本地 CI 复现工具 act 使用指南

**Checkpoint**: ✅ 基础设施就绪 - 用户故事实施可以并行开始

---

## Phase 3: User Story 1 - 代码变更时自动化测试 (Priority: P1) 🎯 MVP

**Goal**: 实现自动化测试工作流,在代码推送时自动运行质量检查和测试

**Independent Test**: 推送代码到功能分支,验证 GitHub Actions 自动运行测试并在 2 分钟内显示结果

### Implementation for User Story 1

- [X] T009 [US1] 创建 .github/workflows/test.yml 测试工作流(参考 contracts/test-workflow.yml)
- [X] T010 [US1] 配置 test.yml 的触发条件(push 到所有分支,PR 事件)
- [X] T011 [US1] 在 test.yml 中添加 Python 3.12 和 uv 设置步骤
- [X] T012 [US1] 在 test.yml 中添加依赖安装步骤(uv sync --frozen)
- [X] T013 [US1] 在 test.yml 中添加 ruff linter 检查步骤
- [X] T014 [US1] 在 test.yml 中添加 ruff format 检查步骤
- [X] T015 [US1] 在 test.yml 中添加 mypy 类型检查步骤
- [X] T016 [US1] 在 test.yml 中添加 pytest 测试步骤(包含覆盖率 ≥80% 要求)
- [X] T017 [US1] 在 test.yml 中添加覆盖率报告上传步骤(artifact)
- [X] T018 [US1] 在 test.yml 中添加 PR 评论步骤(测试失败时)
- [ ] T019 [US1] 配置 GitHub 分支保护规则要求 test workflow 通过 (需要在 GitHub 上手动配置)

**Test Validation for US1**:
- [ ] T020 [US1] 推送代码到测试分支验证 workflow 触发 (待 PR 创建后验证)
- [ ] T021 [US1] 验证所有质量检查步骤按预期执行 (待 PR 创建后验证)
- [ ] T022 [US1] 验证测试失败时 PR 被阻止合并 (需要分支保护规则配置)
- [ ] T023 [US1] 验证覆盖率低于 80% 时构建失败 (待 PR 创建后验证)

**Checkpoint**: ✅ 用户故事 1 代码实现完成 - 等待推送验证

---

## Phase 4: User Story 2 - 自动化部署到阿里云 ECS (Priority: P2)

**Goal**: 实现自动化部署工作流,当代码合并到 master 时自动部署到阿里云 ECS

**Independent Test**: 合并 PR 到 master,验证应用在 10 分钟内在阿里云 ECS 上更新

### Prerequisites for User Story 2

- [ ] T024 [US2] 配置 GitHub Secrets: ALIYUN_ECS_HOST (需要在 GitHub 上手动配置)
- [ ] T025 [US2] 配置 GitHub Secrets: ALIYUN_SSH_USER (需要在 GitHub 上手动配置)
- [ ] T026 [US2] 配置 GitHub Secrets: ALIYUN_SSH_PRIVATE_KEY (需要在 GitHub 上手动配置)
- [ ] T027 [US2] 在 ECS 上创建 deploy 用户并配置 SSH 密钥 (需要 ECS 服务器访问)
- [ ] T028 [US2] 在 ECS 上配置 sudo 权限(仅限 systemctl restart diting) (需要 ECS 服务器访问)
- [ ] T029 [US2] 在 ECS 上创建 /opt/diting/releases 目录结构 (需要 ECS 服务器访问)
- [ ] T030 [US2] 在 ECS 上安装 diting.service 到 /etc/systemd/system/ (需要 ECS 服务器访问)

### Implementation for User Story 2

- [X] T031 [US2] 创建 .github/workflows/deploy.yml 部署工作流(参考 contracts/deploy-workflow.yml)
- [X] T032 [US2] 配置 deploy.yml 触发条件(仅 push 到 master 分支)
- [X] T033 [US2] 配置 deploy.yml concurrency 设置(group: production-deploy, cancel-in-progress: false)实现串行执行
- [X] T034 [US2] 在 deploy.yml 中添加 SSH 密钥配置步骤(webfactory/ssh-agent)
- [X] T035 [US2] 在 deploy.yml 中添加 known_hosts 配置步骤
- [X] T036 [US2] 在 deploy.yml 中添加创建版本目录步骤(timestamp-based release ID)
- [X] T037 [US2] 在 deploy.yml 中添加代码上传步骤(rsync with excludes)
- [X] T038 [US2] 在 deploy.yml 中添加依赖安装步骤(uv sync --frozen)
- [X] T039 [US2] 在 deploy.yml 中添加符号链接更新步骤(current + previous)
- [X] T040 [US2] 在 deploy.yml 中添加服务重启步骤(systemctl restart)
- [X] T041 [US2] 在 deploy.yml 中添加健康检查步骤(HTTP /health + JSON验证 + 服务状态)
- [X] T042 [US2] 在 deploy.yml 中添加回滚步骤(健康检查失败时)
- [X] T043 [US2] 在 deploy.yml 中添加旧版本清理步骤(保留最近3个 + 清理7天前)
- [X] T044 [US2] 在 deploy.yml 中添加失败通知步骤(创建 GitHub Issue)

**Test Validation for US2**:
- [ ] T045 [US2] 创建测试 PR 并合并到 master 验证部署触发
- [ ] T046 [US2] 验证部署成功并通过健康检查
- [ ] T047 [US2] 验证版本目录和符号链接正确创建
- [ ] T048 [US2] 故意引入错误验证回滚机制工作
- [ ] T049 [US2] 快速连续合并两个 PR 验证串行执行(concurrency)
- [ ] T050 [US2] 验证旧版本自动清理机制

**Checkpoint**: 用户故事 2 完成 - 自动化部署流程完全可用

---

## Phase 5: User Story 3 - 部署状态可见性 (Priority: P3)

**Goal**: 提供部署状态、历史和日志的可见性,便于团队追踪和调试

**Independent Test**: 检查 GitHub Actions 界面,验证可以快速识别部署状态和查看详细日志

### Implementation for User Story 3

- [ ] T051 [P] [US3] 在 test.yml 中添加 workflow 状态徽章到 README.md
- [ ] T052 [P] [US3] 在 deploy.yml 中添加 workflow 状态徽章到 README.md
- [ ] T053 [US3] 在 deploy.yml 中添加部署成功总结输出(版本、提交SHA、作者)
- [ ] T054 [US3] 在 deploy.yml 中添加部署时长统计输出
- [ ] T055 [US3] 优化 workflow 日志输出格式(使用 echo 分组和颜色)
- [ ] T056 [US3] 在失败的 GitHub Issue 中包含部署日志链接和错误摘要
- [ ] T057 [US3] 创建 docs/ci-cd/troubleshooting.md 故障排查指南(链接到常见错误模式)

**Test Validation for US3**:
- [ ] T058 [US3] 验证 README 徽章正确显示 workflow 状态
- [ ] T059 [US3] 验证部署成功后输出包含所有关键信息
- [ ] T060 [US3] 验证失败的 Issue 包含足够的调试信息
- [ ] T061 [US3] 团队成员测试:从 Actions 页面识别部署状态 < 30秒

**Checkpoint**: 用户故事 3 完成 - 部署可见性和可调试性完全实现

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 最终优化、文档完善和性能调优

- [ ] T062 [P] 更新 quickstart.md 添加实际部署验证步骤
- [ ] T063 [P] 创建 docs/ci-cd/workflows-overview.md 工作流总览文档
- [ ] T064 [P] 在 test.yml 中添加缓存优化(uv cache)
- [ ] T065 [P] 在 deploy.yml 中添加部署超时保护(timeout-minutes: 15)
- [ ] T066 [P] 验证所有 workflow 符合 GitHub Actions 最佳实践
- [ ] T067 [P] 使用 actionlint 验证 workflow 文件语法
- [ ] T068 [P] 审查并更新所有 GitHub Secrets 的文档说明
- [ ] T069 测试完整端到端流程:功能分支 → PR → 测试 → 合并 → 部署
- [ ] T070 验证所有成功标准(SC-001 到 SC-009)全部满足
- [ ] T071 创建 PR 到 master 完成此功能

---

## Dependencies & Execution Strategy

### User Story Dependencies

```
Phase 1 (Setup)
  ↓
Phase 2 (Foundational - 健康检查端点)
  ↓
  ├─→ Phase 3 (US1: 自动化测试) ✅ 独立实施
  │   ↓
  ├─→ Phase 4 (US2: 自动化部署) ✅ 依赖 US1(需要测试通过才能部署)
  │   ↓
  └─→ Phase 5 (US3: 状态可见性) ✅ 增强 US1 和 US2
      ↓
Phase 6 (Polish)
```

### MVP Scope 🎯

**Minimum Viable Product** = Phase 1 + Phase 2 + Phase 3 (User Story 1)

交付价值:
- ✅ 自动化测试保护代码质量
- ✅ 健康检查端点可用
- ✅ 80% 测试覆盖率强制执行

### Parallel Execution Opportunities

**Phase 1 内部**: 所有任务可并行(T001-T003)

**Phase 2 内部**: T005-T008 可并行执行

**Phase 3 (US1)**:
- 基础配置完成后(T009-T012),T013-T017 可并行添加检查步骤
- 验证任务 T020-T023 可并行执行

**Phase 4 (US2)**:
- Prerequisites T024-T030 可分为两组:
  - Group A: GitHub Secrets (T024-T026) 并行
  - Group B: ECS 配置 (T027-T030) 并行
- Workflow 步骤 T033-T044 大多串行(按部署流程)

**Phase 5 (US3)**: T051-T052 并行,T053-T057 可并行

**Phase 6**: 大部分任务(T062-T068)可并行执行

### Implementation Strategy

1. **Week 1: MVP** - Phase 1-3 (自动化测试流程)
   - 立即交付价值:保护代码质量
   - 验收:推送代码触发测试,失败阻止合并

2. **Week 2: 核心部署** - Phase 4 (自动化部署)
   - ECS 准备工作可能需要 1-2 天
   - 首次手动部署验证环境
   - 自动化部署流程

3. **Week 3: 可见性和优化** - Phase 5-6
   - 增强可调试性
   - 性能优化
   - 文档完善

---

## Task Summary

**Total Tasks**: 71
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 5 tasks
- Phase 3 (US1 - 自动化测试): 15 tasks
- Phase 4 (US2 - 自动化部署): 27 tasks
- Phase 5 (US3 - 状态可见性): 11 tasks
- Phase 6 (Polish): 10 tasks

**Parallel Opportunities**: ~25 tasks 可并行(标记 [P])

**User Stories**:
- US1 (P1): 15 tasks - 自动化测试 🎯 MVP
- US2 (P2): 27 tasks - 自动化部署
- US3 (P3): 11 tasks - 状态可见性

**Estimated Timeline**: 2-3 weeks
- MVP (US1): 3-5 days
- Full Feature: 2-3 weeks

---

## Validation Checklist

完成所有任务后,验证以下成功标准:

- [ ] **SC-001**: 推送代码后 5 分钟内收到测试结果
- [ ] **SC-002**: 测试失败的代码无法合并到 master
- [ ] **SC-003**: master 合并后 10 分钟内完成部署
- [ ] **SC-004**: 部署成功率 > 95%
- [ ] **SC-005**: 常规发布无需任何手动步骤
- [ ] **SC-006**: 失败部署自动回滚,零停机
- [ ] **SC-007**: 30 秒内可以识别部署状态
- [ ] **SC-008**: 无凭证泄露(扫描仓库和日志)
- [ ] **SC-009**: 代码测试覆盖率 ≥ 80%

✅ **所有检查项通过 = 功能完成**
