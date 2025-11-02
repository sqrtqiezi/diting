# Implementation Plan: GitHub CI/CD 与阿里云 ECS 部署

**Branch**: `005-github-ci-aliyun-deploy` | **Date**: 2025-11-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-github-ci-aliyun-deploy/spec.md`

## Summary

实现基于 GitHub Actions 的自动化测试和部署流程,当代码推送时自动运行质量检查和测试,当合并到 master 分支时自动部署到阿里云 ECS 服务器。

**技术方案**:
- 使用 GitHub Actions 实现 CI/CD 流水线
- 通过 SSH 和 rsync 部署到阿里云 ECS
- 基于符号链接的零停机部署和回滚
- Systemd 服务管理和健康检查验证

## Technical Context

**Language/Version**: Python 3.12.6(已安装)+ YAML(GitHub Actions 配置)+ Bash(部署脚本)
**Primary Dependencies**: GitHub Actions, rsync, SSH, systemd, uv
**Storage**: 文件系统(版本目录 /opt/diting/releases/)+ GitHub Actions 元数据 + journald 日志
**Testing**: pytest(单元/集成测试), ruff(代码检查), mypy(类型检查)
**Target Platform**: Ubuntu 22.04 LTS on 阿里云 ECS + GitHub Actions Runner(ubuntu-latest)
**Project Type**: Single project(DevOps 基础设施,不涉及应用代码结构变更)
**Performance Goals**:
- 测试反馈 < 5 分钟
- 部署完成 < 10 分钟
- 健康检查响应 < 100ms
**Constraints**:
- 单服务器部署(无负载均衡)
- 零停机时间要求
- GitHub Actions 免费额度限制(2000 分钟/月)
**Scale/Scope**:
- 1 个生产环境
- 保留最近 3 个部署版本
- 支持当前项目规模(小型微服务)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**状态**: ✅ PASSED (无宪法文件,跳过检查)

**说明**: 项目当前没有 `.specify/constitution.md` 文件,因此没有复杂度限制。此功能为 DevOps 基础设施,不增加应用程序复杂度。

## Project Structure

### Documentation (this feature)

```text
specs/005-github-ci-aliyun-deploy/
├── spec.md              # 功能规范(已完成)
├── plan.md              # 本文件 - 实施计划
├── research.md          # 技术研究和选型(已完成)
├── data-model.md        # CI/CD 数据模型(已完成)
├── quickstart.md        # 快速上手指南(已完成)
├── contracts/           # 接口契约(已完成)
│   ├── README.md
│   ├── test-workflow.yml
│   ├── deploy-workflow.yml
│   ├── systemd-service.service
│   └── health-endpoint.md
└── tasks.md             # 任务分解(待生成,使用 /speckit.tasks)
```

### Source Code (repository root)

此功能主要涉及 **DevOps 配置文件**,不修改现有应用代码结构。

```text
.github/
└── workflows/          # 新增 - GitHub Actions 工作流
    ├── test.yml        # 自动化测试工作流
    └── deploy.yml      # 自动化部署工作流

src/
├── endpoints/
│   └── wechat/
│       └── webhook_app.py  # 需要添加 /health 端点
├── models/             # 现有,无变更
├── services/           # 现有,无变更
└── cli/                # 现有,无变更

tests/
├── unit/
│   └── endpoints/
│       └── wechat/
│           └── test_health.py  # 新增 - 健康检查测试
├── integration/        # 现有,无变更
└── contract/           # 现有,无变更

deploy/                 # 新增 - 部署相关文件(可选)
└── diting.service      # Systemd 服务文件(参考,实际部署到服务器)
```

**Structure Decision**: 选择 Option 1 (Single project),因为这是 DevOps 基础设施功能,不改变应用程序架构。主要变更:
1. 添加 `.github/workflows/` 目录存放 CI/CD 配置
2. 在现有 `webhook_app.py` 中添加 `/health` 端点
3. 添加健康检查测试用例

**不涉及的目录**:
- 无需创建新的服务或模型
- 无需修改现有业务逻辑
- 无需添加数据库迁移

## Complexity Tracking

**无复杂度违规** - 此部分不适用

此功能是 DevOps 基础设施,不增加应用程序复杂度。所有变更都是标准的 CI/CD 最佳实践。

## Implementation Phases

### Phase 0: 技术研究 ✅ 已完成

**输出**: [research.md](./research.md)

**关键决策**:
- CI/CD 平台: GitHub Actions
- 部署方式: SSH + Systemd
- 健康检查: HTTP /health 端点
- 回滚策略: 符号链接切换

### Phase 1: 设计文档 ✅ 已完成

**输出**:
- [data-model.md](./data-model.md) - CI/CD 数据实体
- [contracts/](./contracts/) - Workflow 和 API 契约
- [quickstart.md](./quickstart.md) - 快速上手指南

**关键设计**:
- Workflow 文件格式和触发条件
- Systemd 服务配置
- 健康检查端点规范
- 版本管理策略

### Phase 2: 任务分解 ⏳ 待执行

**命令**: `/speckit.tasks`

**预期输出**: [tasks.md](./tasks.md)

**任务类型**:
1. **代码实现**: 添加 /health 端点和测试
2. **配置文件**: 创建 workflow 文件
3. **服务器准备**: 配置 ECS 环境
4. **验证测试**: 端到端测试 CI/CD 流程

### Phase 3: 实施执行 ⏳ 待执行

**命令**: `/speckit.implement`

**执行顺序**:
1. 本地开发和测试(User Story 1 相关)
2. ECS 服务器配置(User Story 2 前置条件)
3. GitHub 配置(Secrets, Workflows)
4. 首次部署验证
5. 完整流程测试

## Next Steps

1. **生成任务列表**:
   ```bash
   /speckit.tasks
   ```

2. **开始实施**:
   ```bash
   /speckit.implement
   ```

3. **持续跟踪**:
   - 使用 GitHub Projects 跟踪任务进度
   - 使用 GitHub Actions 查看 CI/CD 运行历史
   - 使用 journald 监控服务器日志

## Related Documentation

- **Specification**: [spec.md](./spec.md) - 功能需求和用户故事
- **Research**: [research.md](./research.md) - 技术选型和可行性分析
- **Data Model**: [data-model.md](./data-model.md) - CI/CD 数据实体设计
- **Contracts**: [contracts/](./contracts/) - Workflow 和 API 契约
- **Quickstart**: [quickstart.md](./quickstart.md) - 快速上手指南
- **Tasks**: [tasks.md](./tasks.md) - 任务分解(待生成)

## Success Validation

完成实施后,验证以下成功标准:

- [ ] **SC-001**: 推送代码后 5 分钟内收到测试结果
- [ ] **SC-002**: 测试失败的代码无法合并到 master
- [ ] **SC-003**: master 合并后 10 分钟内完成部署
- [ ] **SC-004**: 部署成功率 > 95%
- [ ] **SC-005**: 常规发布无需任何手动步骤
- [ ] **SC-006**: 失败部署自动回滚,零停机
- [ ] **SC-007**: 30 秒内可以识别部署状态
- [ ] **SC-008**: 无凭证泄露(扫描仓库和日志)
