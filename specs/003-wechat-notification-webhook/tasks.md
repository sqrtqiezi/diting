# Tasks: 微信通知消息接收服务

**输入**: 设计文档来自 `/specs/003-wechat-notification-webhook/`
**前置条件**: plan.md, spec.md, research.md, data-model.md, contracts/webhook-api.yaml

**测试**: 根据规范要求包含测试任务(测试覆盖率 ≥80%)。先编写测试,确保测试失败后再实现功能。

**组织方式**: 任务按用户故事分组,以便每个故事可以独立实现和测试。

## 格式: `[ID] [P?] [Story] 描述`

- **[P]**: 可并行执行(不同文件,无依赖关系)
- **[Story]**: 任务所属的用户故事(例如: US1, US2, US3)
- 描述中包含具体文件路径

## 路径约定

单项目结构:
- 源代码: `src/diting/`
- 测试: `tests/`
- 配置: `config/`
- 日志: `logs/`

---

## 阶段 1: 初始化 (共享基础设施)

**目的**: 项目初始化和基础结构搭建

- [X] T001 创建目录结构: `src/diting/endpoints/wechat/` 用于 webhook 模块, `logs/` 用于日志文件, `config/` 用于配置
- [X] T002 在 pyproject.toml 中添加 FastAPI 和 uvicorn 依赖 (fastapi>=0.104.0, uvicorn[standard]>=0.24.0)
- [X] T003 [P] 创建空占位文件: `src/diting/endpoints/wechat/webhook_app.py`, `webhook_handler.py`, `webhook_logger.py`, `webhook_config.py`
- [X] T004 [P] 创建测试目录结构: `tests/unit/endpoints/wechat/`, `tests/integration/endpoints/wechat/`, `tests/contract/endpoints/wechat/`
- [X] T005 [P] 创建 `config/webhook.yaml` 包含默认配置(主机、端口、日志设置)
- [X] T006 [P] 创建 `logs/.gitkeep` 确保日志目录在 git 中存在

---

## 阶段 2: 基础设施 (阻塞性前置条件)

**目的**: 必须在任何用户故事实现之前完成的核心基础设施

**⚠️ 关键**: 在此阶段完成前,不能开始任何用户故事的工作

- [X] T007 在 `src/diting/endpoints/wechat/webhook_config.py` 中实现 WebhookConfig 模型,基于 data-model.md (pydantic BaseSettings)
- [X] T008 [P] 在 `src/diting/endpoints/wechat/webhook_handler.py` 中实现 WebhookRequest dataclass 用于原始请求捕获
- [X] T009 [P] 在 `src/diting/endpoints/wechat/webhook_app.py` 中实现 HealthStatus 模型用于健康检查响应
- [X] T010 在 `src/diting/endpoints/wechat/webhook_logger.py` 中配置 structlog 和 RotatingFileHandler (100MB × 10 个文件)
- [X] T011 在 `src/diting/endpoints/wechat/webhook_app.py` 中创建 FastAPI 应用实例,包含生命周期事件
- [X] T012 [P] 在 `src/diting/endpoints/wechat/webhook_app.py` 中实现全局异常处理器,处理未捕获错误
- [X] T013 [P] 在 `tests/unit/endpoints/wechat/test_webhook_config.py` 中添加 WebhookConfig 的单元测试

**检查点**: 基础设施就绪 - 现在可以并行开始用户故事的实现

---

## 阶段 3: 用户故事 1 - 接收并记录微信通知消息 (优先级: P1) 🎯 MVP

**目标**: 接收来自第三方微信转发服务的 webhook 推送,将所有消息完整记录到结构化日志中,不做格式假设

**独立测试方法**:
1. 启动服务 `python cli.py serve`
2. 发送任意格式的 POST 请求到 `http://localhost:8000/webhook/wechat`
3. 验证立即返回 200 OK
4. 检查 `logs/wechat_webhook.log` 包含完整的请求数据(headers, body_text, parsed_json/parse_error)

### 用户故事 1 的测试任务

> **注意: 先编写这些测试,确保测试失败后再实现功能**

- [X] T014 [P] [US1] 在 `tests/contract/endpoints/wechat/test_webhook_api.py` 中为 POST /webhook/wechat 编写契约测试(验证 OpenAPI schema)
- [X] T015 [P] [US1] 在 `tests/unit/endpoints/wechat/test_webhook_handler.py` 中为 log_webhook_request 函数编写单元测试(mock logger)
- [X] T016 [P] [US1] 在 `tests/integration/endpoints/wechat/test_webhook_app.py` 中为 webhook 消息流程编写集成测试(使用 TestClient 端到端测试)

### 用户故事 1 的实现任务

- [X] T017 [US1] 在 `src/diting/endpoints/wechat/webhook_app.py` 中实现 POST /webhook/wechat 端点(异步、BackgroundTasks、立即返回 200)
- [X] T018 [US1] 在 `src/diting/endpoints/wechat/webhook_handler.py` 中实现 log_webhook_request 函数(读取 body_bytes、尝试解析 JSON/Form、记录原始数据)
- [X] T019 [US1] 在 webhook 端点处理器中添加请求 ID 生成(UUID)
- [X] T020 [US1] 在 webhook_handler.py 中实现多格式解析(JSON、URL 编码表单、纯文本),具备容错能力
- [X] T021 [US1] 在 webhook_logger.py 中添加包含所有请求字段的结构化日志(timestamp, client_ip, headers, body_text, parsed_json, parse_error)
- [X] T022 [US1] 使用各种消息格式测试: JSON、Form、纯文本、二进制、空 body、格式错误的 JSON(验证所有格式都能记录且不崩溃)

**检查点**: 此时,用户故事 1 应该完全可用 - 服务接收任意格式的 webhook,记录完整数据,永不崩溃

---

## 阶段 4: 用户故事 2 - 配置和管理 Webhook 服务 (优先级: P2)

**目标**: 通过命令行工具 `python cli.py serve` 启动和管理 webhook 服务,支持配置参数和优雅关闭

**独立测试方法**:
1. 执行 `python cli.py serve --help` 查看帮助信息
2. 执行 `python cli.py serve --port 8888` 启动服务,验证监听 8888 端口
3. 按 Ctrl+C,验证服务优雅关闭(完成当前请求后退出)

### 用户故事 2 的测试任务

- [X] T023 [P] [US2] 在 `tests/unit/cli/test_serve_command.py` 中为 CLI serve 命令编写单元测试(mock uvicorn.run)
- [X] T024 [P] [US2] 在 `tests/integration/endpoints/wechat/test_webhook_lifecycle.py` 中为服务启动和关闭编写集成测试

### 用户故事 2 的实现任务

- [X] T025 [P] [US2] 使用 Click 在 `cli.py` 中添加 serve 子命令(--config, --host, --port, --log-level 选项)
- [X] T026 [US2] 在 serve 命令中实现从文件和环境变量加载配置
- [X] T027 [US2] 在 serve 命令中实现使用配置启动 uvicorn 服务器(调用 uvicorn.run 传入 FastAPI app)
- [X] T028 [US2] 在 `src/diting/endpoints/wechat/webhook_app.py` 的 lifespan 中实现信号处理器(SIGINT, SIGTERM)用于优雅关闭
- [X] T029 [US2] 在 webhook_app.py 中添加启动日志(服务版本、配置、监听地址)
- [X] T030 [US2] 在 webhook_app.py 中添加关闭日志(服务停止、运行时间)
- [X] T031 [US2] 使用不同配置测试服务启动(端口、日志级别)并验证正确行为

**检查点**: 此时,用户故事 1 和 2 应该都能工作 - 服务可以通过 CLI 启动/停止,接收 webhook

---

## 阶段 5: 用户故事 3 - 服务健康状态检查 (优先级: P3)

**目标**: 提供 GET /health 端点用于监控服务状态,包括日志写入能力检测

**独立测试方法**:
1. 启动服务后,访问 `http://localhost:8000/health`
2. 验证返回 `{"status": "healthy", "version": "1.0.0", "uptime_seconds": N, "message_count": N, "log_writable": true}`
3. 模拟日志写入失败(chmod 000 logs/),再次访问 /health,验证返回 503 unhealthy

### 用户故事 3 的测试任务

- [X] T032 [P] [US3] 在 `tests/contract/endpoints/wechat/test_webhook_api.py` 中为 GET /health 编写契约测试(验证 OpenAPI schema)
- [X] T033 [P] [US3] 在 `tests/unit/endpoints/wechat/test_webhook_app.py` 中为健康检查逻辑编写单元测试(mock log_writable 检查)
- [X] T034 [P] [US3] 在 `tests/integration/endpoints/wechat/test_webhook_health.py` 中为健康/不健康状态编写集成测试

### 用户故事 3 的实现任务

- [X] T035 [P] [US3] 在 `src/diting/endpoints/wechat/webhook_app.py` 中实现 GET /health 端点(返回 HealthStatus 模型)
- [X] T036 [US3] 添加服务运行时间跟踪(在 lifespan 中记录 start_time,在 health 端点中计算 uptime_seconds)
- [X] T037 [US3] 添加消息计数器(每次 webhook 请求时递增,在 health 端点中暴露)
- [X] T038 [US3] 在 `src/diting/endpoints/wechat/webhook_logger.py` 中实现日志可写性检查(尝试写入测试日志条目)
- [X] T039 [US3] 当 log_writable=false 时在 health 端点返回 503 状态码
- [X] T040 [US3] 在正常和降级条件下测试 health 端点(健康、日志写入失败)

**检查点**: 现在所有用户故事都应该独立可用 - webhook 接收消息、CLI 管理服务、health 端点监控状态

---

## 阶段 6: 完善和横切关注点

**目的**: 影响多个用户故事的改进

- [X] T041 [P] 为所有 webhook 模块添加全面的文档字符串(webhook_app.py, webhook_handler.py, webhook_logger.py, webhook_config.py)
- [X] T042 [P] 为所有函数签名添加类型提示(使用 Python 3.12+ 语法)
- [X] T043 运行 ruff check 并修复所有 webhook 模块的 linting 问题
- [X] T044 使用 pytest-cov 验证 webhook 端点的测试覆盖率 ≥80%
- [X] T045 [P] 更新 quickstart.md,包含实际的服务启动输出和日志示例
- [X] T046 [P] 添加性能日志(测量每个 webhook 请求的 processing_time_ms)
- [X] T047 使用并发请求测试(使用 locust 或类似工具发送 100+ 并发 webhook)
- [X] T048 逐步验证 quickstart.md(执行所有命令,验证输出与文档匹配)
- [X] T049 [P] 为边缘情况添加错误处理: 超大请求、网络超时、格式错误的 UTF-8
- [X] T050 最终集成测试: 启动服务、手动配置 notify_url(curl)、发送真实 webhook、验证日志、检查健康状态、停止服务

---

## 依赖关系和执行顺序

### 阶段依赖

- **初始化 (阶段 1)**: 无依赖 - 可立即开始
- **基础设施 (阶段 2)**: 依赖初始化完成 - 阻塞所有用户故事
- **用户故事 (阶段 3-5)**: 都依赖基础设施阶段完成
  - 用户故事可以并行进行(如果有足够人力)
  - 或按优先级顺序执行(P1 → P2 → P3)
- **完善 (阶段 6)**: 依赖所有用户故事完成

### 用户故事依赖

- **用户故事 1 (P1)**: 基础设施(阶段 2)完成后可开始 - 不依赖其他故事
- **用户故事 2 (P2)**: 基础设施(阶段 2)完成后可开始 - 独立于 US1(CLI管理 vs webhook接收)
- **用户故事 3 (P3)**: 基础设施(阶段 2)完成后可开始 - 需要 US1 的消息计数器,但可独立实现

### 每个用户故事内部

- 测试必须先编写并失败后再实现
- 模型先于服务
- 服务先于端点
- 核心实现先于集成
- 故事完成后再进入下一个优先级

### 并行执行机会

- **初始化 (阶段 1)**: T003, T004, T005, T006 可并行
- **基础设施 (阶段 2)**: T008, T009, T012, T013 可并行(不同文件)
- **US1 测试**: T014, T015, T016 可并行编写
- **US2 测试**: T023, T024 可并行编写
- **US2 实现**: T025 (CLI) 与 T028 (优雅关闭)可并行(不同文件)
- **US3 测试**: T032, T033, T034 可并行编写
- **US3 实现**: T035 (端点) 与 T038 (日志检测)可并行(不同文件)
- **完善**: T041, T042, T045, T046, T049 可并行(不同文件或独立关注点)

---

## 并行示例: 用户故事 1

```bash
# 并行启动用户故事 1 的所有测试:
任务: "在 tests/contract/endpoints/wechat/test_webhook_api.py 中为 POST /webhook/wechat 编写契约测试"
任务: "在 tests/unit/endpoints/wechat/test_webhook_handler.py 中为 log_webhook_request 编写单元测试"
任务: "在 tests/integration/endpoints/wechat/test_webhook_app.py 中为 webhook 流程编写集成测试"

# 测试编写并失败后,并行启动模型/处理器:
任务: "在 webhook_app.py 中实现 POST /webhook/wechat 端点"
任务: "在 webhook_handler.py 中实现 log_webhook_request 函数"
# (注意: 这些有一些依赖关系,但可以一起开始然后再集成)
```

## 并行示例: 用户故事 2

```bash
# 并行启动 CLI 和生命周期测试:
任务: "在 tests/unit/cli/test_serve_command.py 中为 CLI serve 编写单元测试"
任务: "在 tests/integration/endpoints/wechat/test_webhook_lifecycle.py 中为生命周期编写集成测试"

# 测试后,并行启动 CLI 和信号处理:
任务: "在 src/diting/cli/__init__.py 中添加 serve 子命令"
任务: "在 webhook_app.py 的 lifespan 中实现信号处理器"
```

---

## 实施策略

### MVP 优先 (仅用户故事 1)

1. 完成阶段 1: 初始化 (6 个任务)
2. 完成阶段 2: 基础设施 (7 个任务) - 关键
3. 完成阶段 3: 用户故事 1 (9 个任务)
4. **停止并验证**:
   - 运行所有 US1 测试(应该通过)
   - 手动启动服务: `python cli.py serve` (MVP 需要最小 CLI)
   - 发送测试 webhook: `curl -X POST http://localhost:8000/webhook/wechat -d '{"test":"data"}'`
   - 检查日志: `tail -f logs/wechat_webhook.log`
5. 如果就绪则部署/演示

### 增量交付

1. 完成初始化 + 基础设施 → 基础就绪 (13 个任务)
2. 添加用户故事 1 → 独立测试 → 交付: webhook接收和日志记录 (MVP!)
3. 添加用户故事 2 → 独立测试 → 交付: CLI服务管理
4. 添加用户故事 3 → 独立测试 → 交付: 健康检查
5. 完善 → 生产就绪

### 并行团队策略

多名开发者时:

1. 团队一起完成初始化 + 基础设施 (13 个任务)
2. 基础设施完成后:
   - 开发者 A: 用户故事 1 (webhook接收, 9 个任务)
   - 开发者 B: 用户故事 2 (CLI管理, 9 个任务)
   - 开发者 C: 用户故事 3 (健康检查, 9 个任务)
3. 故事无缝集成(最小交叉依赖)

---

## 注意事项

- **[P] 任务**: 不同文件或独立关注点,无阻塞依赖
- **[Story] 标签**: 将任务映射到特定用户故事以便追溯
- **测试优先**: 所有测试任务(T014-T016, T023-T024, T032-T034)必须先编写并失败后再实现
- **无格式假设**: US1 任务强调接受任意格式,解析错误时永不崩溃
- **优雅降级**: US3 健康检查检测到日志写入失败但不停止服务
- **配置**: 服务从 config/webhook.yaml、环境变量和 CLI 参数读取配置(优先级: CLI > 环境变量 > 文件)
- **提交频率**: 每个任务或逻辑组完成后提交(例如: 故事的所有测试完成后)
- **检查点**: 在每个用户故事阶段结束时停止,独立验证后再继续
- **性能**: US1 必须在 100ms 内返回 200,后台记录日志(BackgroundTasks)
- **部署**: 不在本规范中 - 将在 004-webhook-deployment 中涵盖
