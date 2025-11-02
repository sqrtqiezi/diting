# 数据模型设计: GitHub CI/CD 与阿里云 ECS 部署

**功能分支**: `004-github-ci-aliyun-deploy`
**日期**: 2025-11-02
**输入**: [spec.md](./spec.md) + [research.md](./research.md)

## 概述

此功能主要涉及 CI/CD 流水线和部署过程的**元数据建模**,而非应用程序数据模型。这些实体主要存在于:
- **GitHub Actions 平台**: Workflow 运行记录、Job 状态、Artifact
- **服务器文件系统**: 部署版本目录、符号链接、日志文件
- **Systemd**: 服务状态、启动日志

**注意**: 这些数据不需要在应用程序中创建数据库表或 Pydantic 模型,而是通过 GitHub API、文件系统操作和 systemd 命令来访问。

## 核心实体

### 实体 1: CI Workflow Run (GitHub Actions 平台)

**描述**: 代表一次 GitHub Actions 工作流执行

**属性**:
- `run_id` (string): GitHub 分配的唯一运行 ID
- `workflow_name` (string): 工作流名称("Test" 或 "Deploy")
- `branch` (string): 触发分支名
- `commit_sha` (string): Git 提交 SHA
- `commit_message` (string): 提交消息
- `author` (string): 提交作者
- `status` (enum): 运行状态
  - `queued`: 等待中
  - `in_progress`: 运行中
  - `completed`: 已完成
- `conclusion` (enum | null): 完成结果(仅当 status=completed 时)
  - `success`: 成功
  - `failure`: 失败
  - `cancelled`: 已取消
  - `skipped`: 已跳过
- `created_at` (datetime): 创建时间
- `started_at` (datetime | null): 开始时间
- `completed_at` (datetime | null): 完成时间
- `duration_seconds` (integer | null): 持续时间(秒)

**关系**:
- 包含多个 `Job`(1:N)
- 链接到 Git `Commit`(1:1)
- 可能触发 `Deployment`(1:0..1)

**访问方式**:
```bash
# GitHub CLI
gh run list --workflow=test.yml --limit=10
gh run view <run_id> --json status,conclusion,createdAt,jobs

# GitHub API
GET /repos/{owner}/{repo}/actions/runs/{run_id}
```

---

### 实体 2: CI Job (GitHub Actions 平台)

**描述**: Workflow Run 中的单个任务(如 "test" 或 "deploy")

**属性**:
- `job_id` (string): Job ID
- `job_name` (string): Job 名称
- `status` (enum): 同 Workflow Run
- `conclusion` (enum | null): 同 Workflow Run
- `started_at` (datetime): 开始时间
- `completed_at` (datetime | null): 完成时间
- `logs_url` (string): 日志下载 URL

**关系**:
- 属于一个 `Workflow Run`(N:1)
- 包含多个 `Step`(1:N)

**访问方式**:
```bash
gh run view <run_id> --log --job=<job_id>
```

---

### 实体 3: Deployment Release (服务器文件系统)

**描述**: 部署到 ECS 的应用程序版本

**属性**:
- `release_id` (string): 时间戳格式,如 "1730534400"
- `release_path` (string): 服务器路径,如 "/opt/diting/releases/1730534400"
- `commit_sha` (string): 对应的 Git 提交 SHA
- `deployed_at` (datetime): 部署时间(从目录创建时间推断)
- `is_current` (boolean): 是否为当前激活版本
- `is_previous` (boolean): 是否为上一个版本(回滚用)
- `size_bytes` (integer): 版本目录大小
- `status` (enum): 部署状态
  - `uploading`: 上传中
  - `installing`: 安装依赖中
  - `activating`: 激活中
  - `active`: 已激活
  - `failed`: 失败
  - `rolled_back`: 已回滚

**关系**:
- 链接到 Git `Commit`(1:1)
- 可能关联 `Deployment Record`(1:0..1)

**访问方式**:
```bash
# 列出所有版本
ssh deploy@$ECS_HOST "ls -lt /opt/diting/releases/"

# 检查当前版本
ssh deploy@$ECS_HOST "readlink /opt/diting/current"

# 检查上一个版本
ssh deploy@$ECS_HOST "readlink /opt/diting/previous"
```

**存储结构**:
```
/opt/diting/
├── releases/
│   ├── 1730534400/  # 最新版本
│   ├── 1730530800/  # 上一个版本
│   └── 1730527200/  # 更早版本
├── current -> releases/1730534400  # 符号链接
└── previous -> releases/1730530800 # 符号链接
```

---

### 实体 4: Service Instance (Systemd)

**描述**: 在 ECS 上运行的应用程务实例

**属性**:
- `service_name` (string): 固定为 "diting.service"
- `status` (enum): 服务状态
  - `active`: 运行中
  - `inactive`: 已停止
  - `failed`: 失败
  - `activating`: 启动中
  - `deactivating`: 停止中
- `pid` (integer | null): 进程 ID
- `memory_usage_bytes` (integer): 内存使用量
- `cpu_usage_percent` (float): CPU 使用率
- `uptime_seconds` (integer): 运行时长
- `restart_count` (integer): 重启次数
- `last_started_at` (datetime): 最后启动时间

**关系**:
- 运行特定的 `Deployment Release`(N:1,通过 /opt/diting/current)

**访问方式**:
```bash
# 检查服务状态
systemctl status diting

# 获取详细信息(JSON)
systemctl show diting --property=ActiveState,SubState,MainPID,MemoryCurrent,ExecMainStartTimestamp

# 查看日志
journalctl -u diting --since "10 minutes ago" --no-pager
```

---

### 实体 5: Health Check Result (临时数据)

**描述**: 部署后健康检查的结果

**属性**:
- `check_id` (string): 检查 ID(通常是 Workflow Run ID)
- `endpoint` (string): 检查的端点,如 "http://localhost:8000/health"
- `status_code` (integer | null): HTTP 状态码
- `response_time_ms` (integer | null): 响应时间(毫秒)
- `response_body` (string | null): 响应内容
- `success` (boolean): 是否成功
- `checked_at` (datetime): 检查时间
- `error_message` (string | null): 错误信息(如果失败)

**关系**:
- 关联到 `Deployment Release`(N:1)
- 关联到 `CI Workflow Run`(N:1)

**访问方式**:
```bash
# 在 GitHub Actions 中执行
curl -f -w "\nTime: %{time_total}s\nStatus: %{http_code}\n" \
  http://localhost:8000/health

# 结果记录在 GitHub Actions 日志中
```

---

## 实体关系图

```
┌─────────────────┐
│ Git Commit      │
│ - sha           │
│ - message       │
│ - author        │
└────────┬────────┘
         │
         │ 1:1
         │
┌────────▼────────────┐      1:N      ┌──────────────┐
│ CI Workflow Run     ├──────────────►│ CI Job       │
│ - run_id            │               │ - job_id     │
│ - workflow_name     │               │ - job_name   │
│ - status            │               │ - status     │
│ - conclusion        │               │ - logs_url   │
│ - duration          │               └──────────────┘
└────────┬────────────┘
         │
         │ 1:0..1 (仅 deploy workflow)
         │
┌────────▼─────────────┐      N:1     ┌──────────────────┐
│ Deployment Release   ├─────────────►│ Service Instance │
│ - release_id         │              │ - service_name   │
│ - release_path       │              │ - status         │
│ - commit_sha         │              │ - pid            │
│ - is_current         │              │ - uptime         │
│ - status             │              └──────────────────┘
└────────┬─────────────┘
         │
         │ 1:N
         │
┌────────▼──────────────┐
│ Health Check Result   │
│ - endpoint            │
│ - status_code         │
│ - success             │
│ - checked_at          │
└───────────────────────┘
```

## 数据生命周期

### CI Workflow Run 数据

**保留策略**:
- GitHub 默认保留 90 天的运行记录
- 日志文件保留 90 天后自动删除
- 可通过 GitHub 设置调整保留时间

**清理方式**:
```bash
# 删除 90 天前的运行记录(需要 admin 权限)
gh api repos/{owner}/{repo}/actions/runs/{run_id} -X DELETE
```

### Deployment Release 数据

**保留策略**:
- 保留最近 3 个版本
- 每次部署成功后自动清理旧版本

**清理脚本**:
```bash
#!/bin/bash
# 在 deploy.yml 中执行

RELEASES_DIR="/opt/diting/releases"
KEEP_COUNT=3

cd "$RELEASES_DIR" || exit 1
ls -t | tail -n +$((KEEP_COUNT + 1)) | xargs -r rm -rf

echo "✅ 清理完成,保留最近 $KEEP_COUNT 个版本"
```

### Service Logs 数据

**保留策略**:
- Systemd 日志默认保留 3 个月
- 配置 journald 限制日志大小

**配置**:
```bash
# /etc/systemd/journald.conf
SystemMaxUse=500M
SystemKeepFree=1G
MaxRetentionSec=3month
```

## 监控与查询

### 常用查询

**1. 查看最近 10 次部署**:
```bash
gh run list --workflow=deploy.yml --limit=10 --json conclusion,createdAt,headBranch,headSha
```

**2. 检查当前部署版本**:
```bash
ssh deploy@$ECS_HOST "
  echo 'Current:' && readlink /opt/diting/current
  echo 'Previous:' && readlink /opt/diting/previous
  echo 'Service Status:' && systemctl is-active diting
"
```

**3. 查看最近失败的运行**:
```bash
gh run list --workflow=test.yml --status=failure --limit=5
```

**4. 检查服务健康状态**:
```bash
ssh deploy@$ECS_HOST "
  curl -f http://localhost:8000/health
  systemctl status diting --no-pager
"
```

## 不涉及的数据模型

以下数据模型**不在此功能范围内**,因为这是 CI/CD 基础设施,不涉及应用程序数据:

- ❌ 微信消息记录(属于 003-wechat-notification-webhook)
- ❌ 用户账户数据(未来功能)
- ❌ 配置数据库(当前使用环境变量和 YAML)
- ❌ 审计日志数据库(当前使用 GitHub Actions 日志和 journald)

## 扩展考虑

虽然当前范围外,但未来可能需要的数据模型:

### 部署元数据数据库(未来)

如果需要更复杂的部署分析和审计,可以考虑创建:

```python
# 未来可能的 Pydantic 模型
class DeploymentRecord(BaseModel):
    """部署记录(存储在数据库中供分析)"""
    id: UUID
    release_id: str
    commit_sha: str
    deployed_by: str  # GitHub username
    deployed_at: datetime
    deployment_duration_seconds: int
    health_check_passed: bool
    rolled_back: bool
    environment: str  # "production" | "staging"

class DeploymentMetric(BaseModel):
    """部署指标(DORA metrics)"""
    deployment_frequency: float  # 每天部署次数
    lead_time_minutes: int  # 从 commit 到部署的时间
    mttr_minutes: int  # 平均恢复时间
    change_failure_rate: float  # 失败率
```

但当前阶段不需要实现这些模型。
