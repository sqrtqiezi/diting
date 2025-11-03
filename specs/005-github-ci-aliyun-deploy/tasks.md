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

- [x] T001 创建 .github/workflows/ 目录结构 ✅
- [x] T002 创建 deploy/ 目录用于部署配置文件 ✅
- [x] T003 创建 docs/ci-cd/ 目录用于 CI/CD 文档 ✅

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 核心基础设施,必须在任何用户故事之前完成

**⚠️ CRITICAL**: 所有用户故事工作必须等待此阶段完成

- [x] T004 验证 src/diting/endpoints/wechat/webhook_app.py 中的 /health 健康检查端点是否存在,如不存在则实现 ✅
- [x] T005 [P] 验证 tests/unit/endpoints/wechat/test_webhook_app_health.py 健康检查单元测试是否存在,如不存在则创建 ✅
- [x] T006 [P] 创建 deploy/diting.service systemd 服务配置文件(参考 specs/005-github-ci-aliyun-deploy/contracts/systemd-service.service) ✅
- [x] T007 [P] 创建 docs/ci-cd/environment-differences.md 环境差异文档(说明本地与 CI 环境的差异) ✅
- [x] T008 [P] 创建 docs/ci-cd/act-setup.md 本地 CI 复现工具 act 使用指南 ✅

**Checkpoint**: ✅ 基础设施就绪 - 用户故事实施可以并行开始

---

## Phase 3: User Story 1 - 代码变更时自动化测试 (Priority: P1) 🎯 MVP

**Goal**: 实现自动化测试工作流,在代码推送时自动运行质量检查和测试

**Independent Test**: 推送代码到功能分支,验证 GitHub Actions 自动运行测试并在 5 分钟内显示结果

### Implementation for User Story 1

- [x] T009 [US1] 创建 .github/workflows/test.yml 测试工作流(基于 specs/005-github-ci-aliyun-deploy/contracts/test-workflow.yml) ✅
- [x] T010 [US1] 在 test.yml 中配置触发条件(push 到所有分支,pull_request 事件:opened/synchronize/reopened) ✅
- [x] T011 [US1] 在 test.yml 中添加 permissions 配置(contents:read, pull-requests:write) ✅
- [x] T012 [US1] 在 test.yml 中添加 Python 3.12 设置步骤(actions/setup-python@v5) ✅
- [x] T013 [US1] 在 test.yml 中添加 uv 安装和缓存步骤(astral-sh/setup-uv@v3) ✅
- [x] T014 [US1] 在 test.yml 中添加依赖安装步骤(uv sync --frozen) ✅
- [x] T015 [US1] 在 test.yml 中添加 ruff linter 检查步骤(uv run ruff check .) ✅
- [x] T016 [US1] 在 test.yml 中添加 ruff format 检查步骤(uv run ruff format --check .) ✅
- [x] T017 [US1] 在 test.yml 中添加 mypy 类型检查步骤(uv run mypy src) ✅
- [x] T018 [US1] 在 test.yml 中添加 pytest 测试步骤(包含 --cov-fail-under=80 覆盖率要求) ✅
- [x] T019 [US1] 在 test.yml 中添加覆盖率报告上传步骤(actions/upload-artifact@v4) ✅
- [x] T020 [US1] 在 test.yml 中添加 PR 失败评论步骤(actions/github-script@v7) ✅
- [x] T021 [US1] 在 test.yml 中添加 timeout-minutes: 10 超时保护 ✅

**Manual Configuration Tasks for US1**:
- [x] T022 [US1] 配置 GitHub 分支保护规则要求 test workflow 通过(Settings → Branches → master) ✅
- [x] T023 [US1] 在分支保护规则中启用 "Require status checks to pass before merging" ✅
- [x] T024 [US1] 在分支保护规则中选择 "test" job 作为必需检查 ✅

**Test Validation for US1**:
- [x] T025 [US1] 推送代码到测试分支验证 workflow 自动触发 ✅
- [x] T026 [US1] 验证所有质量检查步骤(ruff, mypy, pytest)按预期执行 ✅
- [x] T027 [US1] 故意引入代码错误验证测试失败时 PR 被阻止合并 ✅
- [x] T028 [US1] 验证覆盖率低于 80% 时构建失败 ✅

**Checkpoint**: ✅ 用户故事 1 完成 - 自动化测试流程完全可用

---

## Phase 4: User Story 2 - 自动化部署到阿里云 ECS (Priority: P2)

**Goal**: 实现自动化部署工作流,当代码合并到 master 时自动部署到阿里云 ECS

**Independent Test**: 合并 PR 到 master,验证应用在 10 分钟内在阿里云 ECS 上更新

### Prerequisites for User Story 2

**GitHub Secrets Configuration** (手动执行):
- [x] T029 [US2] 使用现有 SSH 密钥 ~/keys/deploy.pem (已配置在 ~/.ssh/config 的 diting-server) ✅
- [x] T030 [US2] 配置 GitHub Secret: ALIYUN_ECS_HOST=<ECS_IP> (使用 gh secret set 或 Web UI,从 ~/.ssh/config 获取) ✅
- [x] T031 [US2] 配置 GitHub Secret: ALIYUN_SSH_USER=deploy (使用 gh secret set 或 Web UI) ✅
- [x] T032 [US2] 配置 GitHub Secret: ALIYUN_SSH_PRIVATE_KEY (cat ~/keys/deploy.pem | gh secret set ALIYUN_SSH_PRIVATE_KEY) ✅

**ECS Server Configuration** (手动执行):
- [x] T033 [US2] 在 ECS 上创建 deploy 用户 ✅ 已完成 (SSH 配置显示 User=deploy)
- [x] T034 [US2] 在 ECS 上配置 deploy 用户 SSH 目录和权限 ✅ 已完成
- [x] T035 [US2] 在 ECS 上添加 SSH 公钥到 ~/.ssh/authorized_keys ✅ 已完成 (deploy.pem 已配置)
- [x] T036 [US2] 在 ECS 上配置 sudo 权限(仅限 systemctl 命令,/etc/sudoers.d/deploy) ✅
- [x] T037 [US2] 在 ECS 上安装 Python 3.12(dnf install python3.12 python3.12-devel) ✅
- [x] T038 [US2] 在 ECS 上为 deploy 用户安装 uv(python3.12 -m pip install uv) ✅
- [x] T039 [US2] 在 ECS 上创建部署目录结构(/opt/diting/releases, chown deploy:deploy) ✅
- [x] T040 [US2] 在 ECS 上安装 systemd 服务文件(cp deploy/diting.service /etc/systemd/system/) ✅
- [x] T041 [US2] 在 ECS 上启用 systemd 服务(systemctl enable diting) ✅
- [x] T042 [US2] 在 ECS 上配置防火墙(firewalld 允许 ssh, http, https, 8000/tcp) ✅

### Implementation for User Story 2

- [x] T043 [US2] 创建 .github/workflows/deploy.yml 部署工作流(基于 specs/005-github-ci-aliyun-deploy/contracts/deploy-workflow.yml) ✅
- [x] T044 [US2] 在 deploy.yml 中配置触发条件(仅 push 到 master 分支) ✅
- [x] T045 [US2] 在 deploy.yml 中配置 environment: production 和 timeout-minutes: 15 ✅
- [x] T046 [US2] 在 deploy.yml 中配置 concurrency 设置(group: "production-deploy", cancel-in-progress: false) ✅
- [x] T047 [US2] 在 deploy.yml 中添加检出代码步骤(actions/checkout@v4) ✅
- [x] T048 [US2] 在 deploy.yml 中添加 SSH 密钥配置步骤(webfactory/ssh-agent@v0.9.0) ✅
- [x] T049 [US2] 在 deploy.yml 中添加 known_hosts 配置步骤(ssh-keyscan) ✅
- [x] T050 [US2] 在 deploy.yml 中添加创建版本目录步骤(基于 timestamp 的 RELEASE_ID) ✅
- [x] T051 [US2] 在 deploy.yml 中添加代码上传步骤(rsync 排除 .git, .venv, __pycache__ 等) ✅
- [x] T052 [US2] 在 deploy.yml 中添加远程依赖安装步骤(uv sync --frozen) ✅
- [x] T053 [US2] 在 deploy.yml 中添加符号链接更新步骤(保存 current→previous, 创建新 current) ✅
- [x] T054 [US2] 在 deploy.yml 中添加服务重启步骤(sudo systemctl restart diting) ✅
- [x] T055 [US2] 在 deploy.yml 中添加服务启动等待步骤(systemctl is-active 检查,最多 60 秒) ✅
- [x] T056 [US2] 在 deploy.yml 中添加 HTTP 健康检查步骤(curl http://localhost:8000/health,最多 30 秒) ✅
- [x] T057 [US2] 在 deploy.yml 中添加健康检查失败时回滚步骤(恢复 previous 符号链接) ✅
- [x] T058 [US2] 在 deploy.yml 中添加旧版本清理步骤(保留最近 3 个版本,ls -t | tail -n +4) ✅
- [x] T059 [US2] 在 deploy.yml 中添加部署成功通知步骤(输出版本、提交 SHA、作者) ✅

**Test Validation for US2**:
- [x] T060 [US2] 手动执行首次部署验证 ECS 环境配置正确(参考 quickstart.md 第四步) ✅
- [x] T061 [US2] 创建测试 PR 并合并到 master 验证自动部署触发 ✅ (PR #3 已合并)
- [x] T062 [US2] 验证部署成功并通过健康检查(检查 Actions 日志和 ECS 服务状态) ✅ (Run #19024856260, 1分42秒完成, 健康检查通过)
- [x] T063 [US2] 验证版本目录和符号链接正确创建(ssh 到 ECS 检查 /opt/diting/) ✅ (current→1762147685, previous→1762079484)
- [ ] T064 [US2] 故意引入错误(如语法错误)验证回滚机制工作
- [ ] T065 [US2] 快速连续合并两个 PR 验证串行执行(concurrency 配置)
- [x] T066 [US2] 验证旧版本自动清理机制(检查 /opt/diting/releases/ 仅保留 3 个) ✅ (保留3个版本: 1762147685, 1762147219, 1762145935)

**Checkpoint**: 🎯 用户故事 2 核心功能完成 - 自动化部署流程已验证可用 (T064-T065为可选测试)

---

## Phase 5: User Story 3 - 部署状态可见性 (Priority: P3)

**Goal**: 提供部署状态、历史和日志的可见性,便于团队追踪和调试

**Independent Test**: 检查 GitHub Actions 界面,验证可以在 30 秒内识别部署状态和查看详细日志

### Implementation for User Story 3

- [ ] T067 [P] [US3] 在 README.md 中添加 Test workflow 状态徽章(![Test](https://github.com/.../workflows/test.yml/badge.svg))
- [ ] T068 [P] [US3] 在 README.md 中添加 Deploy workflow 状态徽章(![Deploy](https://github.com/.../workflows/deploy.yml/badge.svg))
- [ ] T069 [US3] 在 deploy.yml 部署成功步骤中添加详细总结输出(版本 ID、提交 SHA、提交消息、作者、部署时间)
- [ ] T070 [US3] 在 deploy.yml 中添加部署时长统计(记录开始时间,计算总时长)
- [ ] T071 [US3] 在 test.yml 和 deploy.yml 中优化日志输出格式(使用 echo "::group::" 分组)
- [ ] T072 [US3] 在 deploy.yml 失败时添加创建 GitHub Issue 步骤(actions/github-script@v7)
- [ ] T073 [US3] 在失败 Issue 中包含部署日志链接和错误摘要
- [ ] T074 [US3] 创建 docs/ci-cd/troubleshooting.md 故障排查指南(常见错误:SSH 失败、健康检查超时、磁盘空间不足)

**Test Validation for US3**:
- [ ] T075 [US3] 验证 README 徽章正确显示 workflow 状态(绿色=成功,红色=失败)
- [ ] T076 [US3] 验证部署成功后输出包含所有关键信息(版本、提交、作者、时长)
- [ ] T077 [US3] 故意触发部署失败验证 Issue 自动创建且包含足够调试信息
- [ ] T078 [US3] 团队成员测试:从 Actions 页面识别最新部署状态 < 30 秒

**Checkpoint**: ✅ 用户故事 3 完成 - 部署可见性和可调试性完全实现

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 最终优化、文档完善和性能调优

- [ ] T079 [P] 更新 specs/005-github-ci-aliyun-deploy/quickstart.md 添加实际部署验证步骤和常见问题解答
- [ ] T080 [P] 创建 docs/ci-cd/workflows-overview.md 工作流总览文档(说明 test.yml 和 deploy.yml 的设计)
- [ ] T081 [P] 在 test.yml 中优化 uv 缓存配置(enable-cache: true, cache-dependency-glob: "uv.lock")
- [ ] T082 [P] 在 deploy.yml 中验证超时保护已配置(timeout-minutes: 15)
- [ ] T083 [P] 使用 actionlint 验证 .github/workflows/test.yml 语法
- [ ] T084 [P] 使用 actionlint 验证 .github/workflows/deploy.yml 语法
- [ ] T085 [P] 在 docs/ci-cd/ 中创建 secrets-management.md 文档(说明所有 GitHub Secrets 的用途和配置方法)
- [ ] T086 [P] 验证所有 workflow 符合 GitHub Actions 最佳实践(使用固定版本、配置权限、避免凭证泄露)
- [ ] T087 测试完整端到端流程:功能分支 → PR → 测试 → 合并 → 部署
- [ ] T088 验证所有成功标准达成(SC-001 到 SC-009,参考 spec.md)
- [ ] T089 创建最终 PR 合并到 master 完成此功能

---

## Dependencies & Execution Strategy

### Phase Dependencies

```
Phase 1 (Setup)
  ↓
Phase 2 (Foundational - 健康检查端点)
  ↓
  ├─→ Phase 3 (US1: 自动化测试) ✅ 独立实施
  │   ↓
  ├─→ Phase 4 (US2: 自动化部署) ⚠️ 依赖 US1(需要测试通过才能部署)
  │   ↓
  └─→ Phase 5 (US3: 状态可见性) ✅ 增强 US1 和 US2
      ↓
Phase 6 (Polish)
```

### User Story Dependencies

- **User Story 1 (P1)**: 可在 Phase 2 完成后开始 - 不依赖其他故事
- **User Story 2 (P2)**: 可在 Phase 2 完成后开始 - 但建议在 US1 完成后再实施(部署前需要测试通过)
- **User Story 3 (P3)**: 可在 Phase 2 完成后开始 - 增强 US1 和 US2 的可见性

### MVP Scope 🎯

**Minimum Viable Product** = Phase 1 + Phase 2 + Phase 3 (User Story 1)

**交付价值**:
- ✅ 自动化测试保护代码质量
- ✅ 健康检查端点可用
- ✅ 80% 测试覆盖率强制执行
- ✅ 测试失败阻止 PR 合并

**预计时间**: 3-5 天

### Parallel Execution Opportunities

**Phase 1**: 所有任务可并行(T001-T003)

**Phase 2**: T005-T008 可并行执行(不同文件)

**Phase 3 (US1)**:
- T009-T014 可串行(构建 test.yml 基础)
- T015-T020 可在 T014 完成后并行添加(不同检查步骤)
- T025-T028 验证任务可并行执行

**Phase 4 (US2)**:
- **Prerequisites**:
  - GitHub Secrets (T029-T032) 可并行
  - ECS 配置 (T033-T042) 可按顺序执行
- **Workflow 实现**: T043-T059 大多串行(按部署流程顺序)
- **验证**: T060-T066 可部分并行

**Phase 5 (US3)**:
- T067-T068 可并行(不同徽章)
- T069-T074 可并行(不同文件或 workflow 不同部分)

**Phase 6**: T079-T086 可并行执行(独立文档和验证任务)

---

## Implementation Strategy

### Week 1: MVP (Phase 1-3)

**目标**: 自动化测试流程上线

1. Day 1-2: 完成 Phase 1 (Setup) + Phase 2 (Foundational)
2. Day 3-4: 完成 Phase 3 (User Story 1 - 自动化测试)
3. Day 5: 验证和调试(T025-T028)

**交付**: 推送代码自动触发测试,失败阻止合并

### Week 2: 核心部署 (Phase 4)

**目标**: 自动化部署流程上线

1. Day 1-2: ECS 服务器准备(T029-T042)
2. Day 3: 首次手动部署验证环境(T060)
3. Day 4-5: 实现自动化部署 workflow (T043-T059)
4. Week 2 末: 端到端测试(T061-T066)

**交付**: 合并到 master 自动部署到 ECS

### Week 3: 可见性和优化 (Phase 5-6)

**目标**: 增强可调试性和文档完善

1. Day 1-2: 实现状态可见性(T067-T078)
2. Day 3-4: 文档和优化(T079-T086)
3. Day 5: 完整验证和收尾(T087-T089)

**交付**: 完整的 CI/CD 流程,文档齐全

---

## Parallel Team Strategy

### 单人开发
按优先级顺序执行:Phase 1 → 2 → 3 → 4 → 5 → 6

### 双人团队
- **Phase 1-2**: 一起完成(关键路径)
- **Phase 3 完成后**:
  - Developer A: Phase 4 (US2 - 部署)
  - Developer B: Phase 5 (US3 - 可见性)
- **Phase 6**: 一起完成验证

### 三人团队
- **Phase 1-2**: 一起完成
- **Phase 3 完成后**:
  - Developer A: Phase 4 (US2 - 部署)
  - Developer B: Phase 5 (US3 - 可见性)
  - Developer C: Phase 6 文档(提前开始)

---

## Task Summary

**Total Tasks**: 89

| Phase | Description | Task Count | Estimated Time |
|-------|-------------|-----------|----------------|
| Phase 1 | Setup | 3 | 30 分钟 |
| Phase 2 | Foundational | 5 | 2 小时 |
| Phase 3 | US1 - 自动化测试 | 20 | 2-3 天 |
| Phase 4 | US2 - 自动化部署 | 38 | 4-6 天 |
| Phase 5 | US3 - 状态可见性 | 12 | 2-3 天 |
| Phase 6 | Polish | 11 | 2-3 天 |

**Parallel Opportunities**: ~30 tasks 可并行(标记 [P])

**User Stories**:
- **US1 (P1)**: 20 tasks - 自动化测试 🎯 MVP
- **US2 (P2)**: 38 tasks - 自动化部署
- **US3 (P3)**: 12 tasks - 状态可见性

**Estimated Timeline**:
- MVP (US1): 3-5 天
- Full Feature: 2-3 周

---

## Validation Checklist

完成所有任务后,验证以下成功标准(来自 spec.md):

- [ ] **SC-001**: 开发者在推送代码后 5 分钟内收到测试结果
- [ ] **SC-002**: 测试失败的代码无法合并到 master(100% 强制执行)
- [ ] **SC-003**: 成功的 master 合并在 10 分钟内完成生产部署
- [ ] **SC-004**: 部署成功率高于 95%(不包括因错误代码导致的故意失败)
- [ ] **SC-005**: 常规发布不需要任何手动部署步骤
- [ ] **SC-006**: 失败的部署自动维持之前的工作版本(零停机时间)
- [ ] **SC-007**: 团队成员在检查 GitHub Actions 后 30 秒内可以识别部署状态
- [ ] **SC-008**: 所有部署凭证安全存储,日志或仓库中零暴露
- [ ] **SC-009**: 代码测试覆盖率保持在 80% 以上

✅ **所有检查项通过 = 功能完成**

---

## Notes for Implementation

### Manual vs Automated Tasks

**手动任务**(需要人工执行):
- T022-T024: GitHub 分支保护规则配置
- T029-T032: GitHub Secrets 配置 (使用现有密钥 ~/keys/deploy.pem)
- T033-T042: ECS 服务器准备 (T033-T035 已完成 ✅)
- T060: 首次手动部署验证

**已完成的手动任务**:
- ✅ T033-T035: ECS deploy 用户和 SSH 配置 (通过 SSH config diting-server 验证)
- ✅ SSH 密钥: 使用现有 ~/keys/deploy.pem
- ✅ ECS 主机: <已配置在 ~/.ssh/config 的 diting-server>
- ✅ SSH 用户: deploy

**自动化任务**(由 LLM 或脚本执行):
- 所有 workflow 文件创建和编辑
- 所有文档创建
- 所有验证测试

### Critical Path

最长串行依赖链:
```
T001 → T004 → T009 → T043 → T060 → T061 → T087
(Setup → Health Check → Test Workflow → Deploy Workflow → Manual Deploy → Auto Deploy → E2E Test)
```

### Risk Mitigation

**风险 1**: ECS 服务器访问延迟
- **缓解**: 提前准备 ECS 环境(Week 1 末开始 T033-T042)

**风险 2**: 首次部署失败
- **缓解**: 先手动部署验证(T060),再实现自动化

**风险 3**: GitHub Actions 配额不足
- **缓解**: 使用 act 本地测试,减少云端运行次数

---

**Generated**: 2025-11-03
**Total Tasks**: 89
**MVP Tasks**: 28 (Phase 1-3)
**Estimated Completion Time**: 2-3 周 (Full Feature), 3-5 天 (MVP)
