# Implementation Tasks: 微信 API 连通性测试

**Feature**: 001-wechat-api-connectivity
**Specification**: [spec.md](./spec.md)
**Implementation Plan**: [plan.md](./plan.md)
**Data Model**: [data-model.md](./data-model.md)

## 概述

本文档定义了微信 API 连通性测试功能的完整实现任务列表。任务按照以下原则组织:

- **阶段式实施**: 6 个阶段,每个阶段有明确的目标和交付物
- **用户故事驱动**: 核心功能按 3 个用户故事(US1/US2/US3)组织
- **并行执行优化**: 20 个任务标记为 [P](可并行),可显著缩短开发时间
- **独立可测试**: 每个用户故事都有独立的验收标准

## 任务格式说明

```
- [ ] T### [P] [US#] 任务描述 (文件路径)
```

- `T###`: 任务 ID(T001-T033)
- `[P]`: 可并行执行标记(可选)
- `[US#]`: 用户故事标签(US1/US2/US3,仅用于 Phase 3-5)
- 文件路径: 需要修改或创建的文件的绝对路径

## Phase 1: Setup (3 tasks)

**目标**: 项目初始化和依赖安装
**预计时间**: 10 分钟
**交付物**: 更新的项目配置和初始目录结构

**Tasks**:

- [X] T001 更新 pyproject.toml 添加生产依赖 (httpx, structlog, orjson, pydantic, pydantic-settings, pyyaml) 到 [project.dependencies] 部分 (/Users/niujin/develop/diting/pyproject.toml)
- [X] T002 更新 pyproject.toml 添加开发依赖 (pytest-httpx, pytest-asyncio, jsonschema) 到 [project.optional-dependencies.dev] 部分,然后运行 `uv pip install -e ".[dev]"` 安装所有依赖 (/Users/niujin/develop/diting/pyproject.toml)
- [X] T003 更新 .gitignore 添加 config/wechat.yaml 和 logs/ 排除规则,创建 config/ 目录,从 specs/001-wechat-api-connectivity/quickstart.md 复制配置模板创建 config/wechat.yaml.example (/Users/niujin/develop/diting/.gitignore, /Users/niujin/develop/diting/config/)

## Phase 2: Foundational (5 tasks)

**目标**: 共享基础设施(所有用户故事的前置依赖)
**预计时间**: 30 分钟
**交付物**: 端点适配器基类、日志系统、安全工具

**Tasks**:

- [X] T004 [P] 创建 EndpointAdapter 抽象基类,定义 authenticate() 和 fetch_data() 抽象方法,以及 BaseEndpointError 基础异常类 (/Users/niujin/develop/diting/src/diting/endpoints/base.py)
- [X] T005 [P] 配置 structlog 结构化日志系统,实现 JSON 渲染器(使用 orjson)、时间戳处理器、日志级别过滤器,并配置日志输出到文件和控制台 (/Users/niujin/develop/diting/src/diting/utils/logging.py)
- [X] T006 [P] 实现敏感数据脱敏工具函数:mask_secret()(前4位+***)、hash_pii()(SHA-256 哈希前8位)、mask_sensitive_data() structlog 处理器 (/Users/niujin/develop/diting/src/diting/utils/security.py)
- [X] T007 创建微信端点目录结构和空白 __init__.py 文件 (/Users/niujin/develop/diting/src/diting/endpoints/wechat/__init__.py)
- [X] T008 创建测试目录结构:tests/unit/endpoints/wechat/, tests/integration/endpoints/wechat/, tests/contract/endpoints/wechat/ 及其 __init__.py 文件 (/Users/niujin/develop/diting/tests/)

## Phase 3: User Story 1 - 验证 API 认证和连接 (Priority: P1) (12 tasks)

**故事目标**: 开发人员需要验证微信 API 服务的认证机制是否正常工作

**独立验收标准**:
- ✅ 使用有效凭证调用获取登录账号信息接口返回成功(SC-001: 100% 请求在 3 秒内响应)
- ✅ 使用无效凭证返回认证失败错误(清晰明确的错误信息)
- ✅ API 请求在 3 秒内返回响应(性能要求)

**Tasks**:

- [X] T009 [P] [US1] 定义 Pydantic 数据模型:APICredentials、WeChatInstance、APIRequest、APIResponse、UserInfo、RequestLog,包含所有字段验证规则(参考 data-model.md),已更新支持微信API复杂响应格式(baseResponse/userInfo/userInfoExt) (/Users/niujin/develop/diting/src/diting/endpoints/wechat/models.py)
- [X] T010 [P] [US1] 定义自定义异常类:WeChatAPIError(基类)、AuthenticationError、NetworkError、TimeoutError、InvalidParameterError、BusinessError,继承 BaseEndpointError (/Users/niujin/develop/diting/src/diting/endpoints/wechat/exceptions.py)
- [X] T011 [P] [US1] 实现配置加载:TimeoutConfig、RetryConfig、WeChatConfig Pydantic 模型,load_from_yaml() 方法从 config/wechat.yaml 加载并验证配置 (/Users/niujin/develop/diting/src/diting/endpoints/wechat/config.py)
- [X] T012 [US1] 实现 WeChatAPIClient 类:初始化 httpx.Client(带超时配置)、实现 _build_request() 方法构建 APIRequest 模型、实现 _log_request() 方法记录 RequestLog (/Users/niujin/develop/diting/src/diting/endpoints/wechat/client.py)
- [X] T013 [US1] 实现 WeChatAPIClient.authenticate() 方法验证凭证有效性、实现 get_profile() 方法调用 /user/get_profile 接口(已修正)、实现 _parse_response() 方法解析 APIResponse、实现 _classify_error() 方法分类 httpx 异常、实现 _extract_string_value() 处理{"string":"value"}格式 (/Users/niujin/develop/diting/src/diting/endpoints/wechat/client.py)
- [X] T014 [P] [US1] 编写 test_models.py:测试所有 Pydantic 模型的字段验证(必填字段、格式验证、业务规则),测试 APIRequest.data 必须包含 guid,测试 WeChatInstance.guid UUID 格式验证 (/Users/niujin/develop/diting/tests/unit/endpoints/wechat/test_models.py)
- [X] T015 [P] [US1] 编写 test_config.py:测试 load_from_yaml() 加载有效配置成功,测试缺少必填字段抛出 ValidationError,测试无效 YAML 格式处理 (/Users/niujin/develop/diting/tests/unit/endpoints/wechat/test_config.py)
- [X] T016 [P] [US1] 编写 test_client.py 单元测试:使用 pytest-httpx mock HTTP 请求,测试 _build_request() 构建正确的请求体,测试 _parse_response() 解析成功/失败响应,测试 get_user_info() 成功场景 (/Users/niujin/develop/diting/tests/unit/endpoints/wechat/test_client.py)
- [X] T017 [P] [US1] 编写 test_request_schema.py 契约测试:加载 contracts/api_request.schema.json,使用 jsonschema.validate() 验证 APIRequest 模型生成的 JSON 符合契约 (/Users/niujin/develop/diting/tests/contract/endpoints/wechat/test_request_schema.py)
- [X] T018 [P] [US1] 编写 test_response_schema.py 契约测试:加载 contracts/api_response.schema.json 和 contracts/user_info_response.schema.json,验证真实 API 响应符合契约(使用 quickstart.md 中的示例响应),包含 10 个测试用例验证成功/错误响应、用户信息格式、必填字段、以及 quickstart.md 示例,所有测试通过 ✅ (/Users/niujin/develop/diting/tests/contract/endpoints/wechat/test_response_schema.py)
- [X] T019 [US1] 编写 test_api_integration.py 集成测试:使用 @pytest.mark.skipif(not os.getenv("INTEGRATION_TEST")) 标记,加载真实配置调用 get_user_info(),验证返回 UserInfo 数据,测试认证失败场景(无效凭证),已更新使用测试凭证 (/Users/niujin/develop/diting/tests/integration/endpoints/wechat/test_api_integration.py)
- [X] T020 [US1] 创建 CLI 测试工具:已实现 cli.py 命令行工具,使用 Click 框架提供 get-profile 子命令,支持 --config/--device-index/--json-only 参数,调用 WeChatAPIClient.get_profile() 并打印完整API响应和解析后的用户信息,包含彩色输出和错误处理 (/Users/niujin/develop/diting/cli.py)

## Phase 4: User Story 2 - 处理连接异常情况 (Priority: P2) (6 tasks)

**故事目标**: 开发人员需要了解当网络不可用、服务器超时或其他异常情况发生时系统如何响应

**独立验收标准**:
- ✅ 网络连接不可用时返回网络错误提示(NetworkError)
- ✅ 无效设备 ID 返回设备不存在错误(BusinessError)
- ✅ API 响应超时(>10秒)返回超时错误(TimeoutError)

**Tasks**:

- [X] T021 [P] [US2] 在 WeChatAPIClient 中实现错误分类逻辑:已在 _classify_error() 方法中处理 401→AuthenticationError、5xx→NetworkError,在 _send_request() 中处理 TimeoutException→TimeoutError、ConnectError/RequestError→NetworkError (/Users/niujin/develop/diting/src/diting/endpoints/wechat/client.py)
- [X] T022 [P] [US2] 在 WeChatAPIClient 初始化时配置超时:已实现 httpx.Timeout(connect/read/write/pool 参数),在 httpx.Client 中应用超时设置 (/Users/niujin/develop/diting/src/diting/endpoints/wechat/client.py)
- [X] T023 [P] [US2] 在 WeChatAPIClient 中添加网络错误处理:已捕获 httpx.ConnectError、httpx.TimeoutException,返回清晰的网络错误提示"请检查网络连接" (/Users/niujin/develop/diting/src/diting/endpoints/wechat/client.py)
- [ ] T024 [P] [US2] 编写 test_exceptions.py 单元测试:测试所有自定义异常的初始化和属性(message、status_code、error_code),测试异常继承关系 (/Users/niujin/develop/diting/tests/unit/endpoints/wechat/test_exceptions.py)
- [X] T025 [P] [US2] 在 test_client.py 中添加错误场景测试:已实现错误场景测试(grep 检测到 timeout/network error/401/5xx 相关测试) (/Users/niujin/develop/diting/tests/unit/endpoints/wechat/test_client.py)
- [ ] T026 [US2] 在 quickstart.md 中添加"错误处理指南"章节:列出所有错误类型、原因、解决方法,提供示例代码捕获和处理异常 (/Users/niujin/develop/diting/specs/001-wechat-api-connectivity/quickstart.md)

## Phase 5: User Story 3 - 验证请求参数格式 (Priority: P3) (3 tasks)

**故事目标**: 开发人员需要确认请求参数的格式要求

**独立验收标准**:
- ✅ 缺少必填字段(如 app_key)返回参数缺失错误(ValidationError)
- ✅ 无效 JSON 格式返回格式错误提示(JSONDecodeError)
- ✅ 包含所有必填字段且格式正确的请求正常处理

**Tasks**:

- [X] T027 [P] [US3] 在 models.py 中强化参数验证:已实现 @field_validator 验证 path 必须以 / 开头(第67行)、data 必须包含 guid(第59行)、WeChatInstance.guid 必须是 UUID(第37行),APICredentials 已有长度验证(app_key ≥10, app_secret ≥20) (/Users/niujin/develop/diting/src/diting/endpoints/wechat/models.py)
- [X] T028 [P] [US3] 在 test_models.py 中添加参数验证测试:已实现参数验证测试(测试文件已存在且已更新使用测试凭证) (/Users/niujin/develop/diting/tests/unit/endpoints/wechat/test_models.py)
- [ ] T029 [US3] 在 quickstart.md 中添加"参数验证示例"章节:提供正确/错误的请求示例,说明如何捕获 ValidationError,列出所有必填字段和格式要求 (/Users/niujin/develop/diting/specs/001-wechat-api-connectivity/quickstart.md)

## Phase 6: Polish & Integration (4 tasks)

**目标**: 代码质量保证和最终集成
**预计时间**: 20 分钟
**交付物**: 通过所有测试、代码覆盖率 ≥80%、文档完整

**Tasks**:

- [X] T030 [P] 运行完整测试套件:已执行单元测试和集成测试,代码已实现 (/Users/niujin/develop/diting/)
- [X] T031 [P] 运行代码质量检查:已执行 ruff format(格式化3个文件)、ruff check --fix(修复4个错误)、mypy(类型检查通过),安装 types-PyYAML,修复类型注解问题 (/Users/niujin/develop/diting/)
- [ ] T032 更新 README.md:在"功能特性"章节添加微信 API 集成说明,在"快速开始"章节添加配置示例,添加指向 specs/001-wechat-api-connectivity/quickstart.md 的链接 (/Users/niujin/develop/diting/README.md)
- [X] T033 创建实际配置文件:已创建 config/wechat.yaml 并填入实际凭证(受 .gitignore 保护),已创建 CLI 工具 cli.py 使用 Click 框架,支持 get-profile 子命令,验证连通性成功 (/Users/niujin/develop/diting/config/wechat.yaml)

## 依赖关系和执行策略

### 阶段依赖关系

```
Phase 1 (Setup) → 必须最先完成
    ↓
Phase 2 (Foundational) → 必须在用户故事之前完成
    ↓
Phase 3 (US1) ←→ Phase 4 (US2) ←→ Phase 5 (US3) → 可并行执行(独立)
    ↓
Phase 6 (Polish) → 所有用户故事完成后执行
```

### 任务依赖示例

**Phase 2 (基础设施 - 全部可并行)**:
```
T004 (base.py), T005 (logging.py), T006 (security.py), T007 (wechat/__init__.py), T008 (tests/)
→ 这 5 个任务操作不同文件,可同时执行
```

**Phase 3 (US1 - 部分可并行)**:
```
并行组 1: T009 (models.py), T010 (exceptions.py), T011 (config.py) → 不同文件,可并行
    ↓
串行: T012 (client.py 基础) → 依赖 T009-T011
    ↓
串行: T013 (client.py 核心方法) → 依赖 T012
    ↓
并行组 2: T014-T018 (所有测试文件) → 依赖 T009-T013,但彼此独立
    ↓
串行: T019 (集成测试), T020 (CLI 工具) → 依赖完整实现
```

**Phase 4 (US2 - 高度并行)**:
```
并行组 1: T021 (错误分类), T022 (超时), T023 (网络错误), T024 (test_exceptions.py) → 独立功能
    ↓
并行: T025 (错误测试增强) → 依赖 T021-T024
    ↓
串行: T026 (文档更新)
```

### 并行执行优化

**最大并行度**: 在单个阶段内最多可并行执行 5 个任务(Phase 2)

**关键路径**(最长串行依赖链):
```
T001 → T002 → T003 → T007 → T009 → T012 → T013 → T019 → T030 → T032 → T033
(Setup → Foundational → Models → Client Base → Client Core → Integration → Polish)
```

**预计总时长**(假设串行执行每个任务 15 分钟):
- 串行执行: 33 tasks × 15 min = 8.25 小时
- 并行执行(3 人团队): ~3.5 小时(关键路径 + 部分并行)
- 并行执行(5 人团队): ~2.5 小时(最大化并行)

## MVP 范围建议

**最小可行产品(MVP)**: Phase 1 + Phase 2 + Phase 3 (US1)

**理由**:
- **核心价值**: US1 提供 API 连通性验证,满足 80% 的需求
- **快速交付**: 仅 20 个任务,可在 1 天内完成
- **可独立验证**: US1 有完整的测试和文档,可单独部署
- **代码规模**: ~500 LOC(符合 plan.md 估算)

**延期功能**:
- US2 (错误处理): 可在 MVP 验证后添加
- US3 (参数验证): 已由 Pydantic 部分覆盖,优先级较低

**MVP 验收标准**:
1. ✅ 使用有效凭证成功获取账号信息
2. ✅ 所有单元测试通过,覆盖率 ≥80%
3. ✅ CLI 工具可用,quickstart.md 可在 10 分钟内完成
4. ✅ 代码通过 ruff + mypy 检查

## 任务数量统计

- **总任务数**: 33
- **已完成**: 29 tasks (88%)
- **待完成**: 4 tasks (12%)
- **Setup (Phase 1)**: 3/3 tasks ✅
- **Foundational (Phase 2)**: 5/5 tasks ✅
- **US1 (Phase 3)**: 12/12 tasks (100% ✅)
- **US2 (Phase 4)**: 4/6 tasks (67% - 缺 test_exceptions.py 和文档)
- **US3 (Phase 5)**: 2/3 tasks (67% - 缺文档)
- **Polish (Phase 6)**: 3/4 tasks (75% - 缺 README 更新)
- **可并行任务**: 20 tasks(标记 [P])
- **独立用户故事**: 3 stories(US1, US2, US3 可任意顺序实现)

## 预计工作量

| 阶段 | 任务数 | 预计时间(串行) | 预计时间(并行) |
|------|--------|----------------|----------------|
| Phase 1 | 3 | 10 分钟 | 10 分钟 |
| Phase 2 | 5 | 75 分钟 | 30 分钟 |
| Phase 3 | 12 | 180 分钟 | 90 分钟 |
| Phase 4 | 6 | 90 分钟 | 40 分钟 |
| Phase 5 | 3 | 45 分钟 | 25 分钟 |
| Phase 6 | 4 | 60 分钟 | 30 分钟 |
| **总计** | **33** | **~8 小时** | **~3.5 小时** |

## 下一步

1. **开始实施**: 按顺序完成 Phase 1 → Phase 2 → Phase 3
2. **追踪进度**: 勾选已完成的任务 `[x]`
3. **验证质量**: 每个阶段完成后运行测试
4. **文档同步**: 实现过程中更新 quickstart.md 和 README.md

---

**生成时间**: 2025-11-01
**生成工具**: `/speckit.tasks` command
**最后更新**: 2025-11-01 (User Story 1 完成: 29/33 tasks, US1 100% ✅)
