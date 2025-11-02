# 接口契约文档

此目录包含 GitHub CI/CD 与阿里云 ECS 部署功能的所有接口契约和配置规范。

## 文件列表

### 1. [test-workflow.yml](./test-workflow.yml)
**类型**: GitHub Actions 工作流配置

**用途**: 自动化测试工作流,在代码推送和 PR 时触发

**关键特性**:
- 运行 ruff linter 和 formatter
- 运行 mypy 类型检查
- 运行 pytest 测试套件
- 生成覆盖率报告
- 失败时阻止 PR 合并

**触发条件**:
- 任何分支的 push 事件
- Pull Request 打开、同步、重新打开

---

### 2. [deploy-workflow.yml](./deploy-workflow.yml)
**类型**: GitHub Actions 工作流配置

**用途**: 自动化部署工作流,在 master 分支合并后触发

**关键特性**:
- SSH 连接到阿里云 ECS
- 基于时间戳的版本管理
- 零停机部署(符号链接切换)
- 部署后健康检查
- 失败自动回滚
- 清理旧版本(保留最近 3 个)

**所需 Secrets**:
- `ALIYUN_ECS_HOST`: ECS 服务器 IP
- `ALIYUN_SSH_USER`: SSH 用户名
- `ALIYUN_SSH_PRIVATE_KEY`: SSH 私钥

---

### 3. [systemd-service.service](./systemd-service.service)
**类型**: Systemd 服务单元文件

**用途**: 管理 Diting 应用程序作为系统服务

**关键特性**:
- 自动重启策略
- 资源限制(内存 1GB, CPU 100%)
- 安全加固(NoNewPrivileges, PrivateTmp)
- 日志输出到 journald

**安装位置**: `/etc/systemd/system/diting.service`

---

### 4. [health-endpoint.md](./health-endpoint.md)
**类型**: HTTP API 契约文档

**用途**: 定义健康检查端点的请求和响应格式

**端点**: `GET /health`

**响应格式**:
```json
{
  "status": "healthy",
  "service": "diting",
  "version": "1.0.0",
  "timestamp": "2025-11-02T10:30:45.123Z",
  "uptime_seconds": 3600
}
```

**性能要求**: < 100ms 响应时间

---

## 使用流程

### 1. 开发阶段
开发者在功能分支上工作,推送代码后:
```
代码 push → test-workflow.yml 触发 → 运行测试 → PR 显示状态
```

### 2. 合并阶段
PR 合并到 master 后:
```
Master 合并 → deploy-workflow.yml 触发 → 部署到 ECS → 健康检查 → 清理旧版本
```

### 3. 部署流程
```
1. 创建版本目录 /opt/diting/releases/{timestamp}
2. 上传代码 (rsync)
3. 安装依赖 (uv sync)
4. 切换符号链接 /opt/diting/current
5. 重启服务 (systemd)
6. 健康检查 (GET /health)
7. 成功 → 清理旧版本 | 失败 → 回滚
```

## 契约测试

### 测试 Workflow 文件

```bash
# 使用 actionlint 验证语法
brew install actionlint
actionlint test-workflow.yml
actionlint deploy-workflow.yml
```

### 测试健康端点

```python
# 运行测试
pytest tests/unit/endpoints/wechat/test_health.py -v
```

### 测试 Systemd 服务

```bash
# 验证服务文件语法
systemd-analyze verify diting.service

# 测试服务启动
sudo systemctl start diting
sudo systemctl status diting
```

## 版本控制

所有契约文件应纳入版本控制:
- ✅ Workflow 文件提交到 `.github/workflows/`
- ✅ Systemd 服务文件提交到仓库根目录或 `deploy/`
- ✅ API 契约文档提交到 `specs/{feature}/contracts/`

## 变更管理

修改契约文件时:
1. 在功能分支上修改
2. 通过 PR 审查
3. 合并后自动生效(对于 workflow 文件)
4. 对于 systemd 服务文件,需要手动更新服务器配置

## 相关文档

- [技术研究 (research.md)](../research.md): 技术选型和可行性研究
- [数据模型 (data-model.md)](../data-model.md): CI/CD 数据实体设计
- [快速上手 (quickstart.md)](../quickstart.md): 本地测试和手动部署指南
