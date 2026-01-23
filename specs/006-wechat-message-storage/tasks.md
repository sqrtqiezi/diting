# Tasks: 微信消息数据湖存储

**Input**: Design documents from `/specs/006-wechat-message-storage/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/storage-api.md

**Tests**: 根据spec.md的宪章要求,本功能需要≥80%测试覆盖率,因此包含测试任务。

**Organization**: 任务按用户故事(US1-US4)分组,每个故事可独立实现和测试。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行运行(不同文件,无依赖)
- **[Story]**: 任务所属的用户故事(US1, US2, US3, US4)
- 包含准确的文件路径

## Path Conventions

本项目采用单项目结构(single project):
- 源代码: `src/`
- 测试: `tests/`
- 数据: `data/`
- 部署: `deploy/`

---

## Phase 1: Setup (共享基础设施) ✅ COMPLETED

**目的**: 项目初始化和基本结构

- [X] T001 创建数据目录结构 (data/messages/raw, data/parquet/messages, data/metadata/checkpoints)
- [X] T002 安装 PyArrow 和 portalocker 依赖 (uv add pyarrow portalocker)
- [X] T003 [P] 创建 src/services/storage/ 模块目录结构
- [X] T004 [P] 创建 tests/unit/, tests/integration/, tests/contract/ 目录

---

## Phase 2: Foundational (阻塞性前置条件) ✅ COMPLETED

**目的**: 所有用户故事依赖的核心基础设施

**⚠️ 关键**: 必须完成此阶段后才能开始任何用户故事

### 基础模型和Schema

- [X] T005 [P] 创建 MessageContent Pydantic 模型 in src/models/message_schema.py
- [X] T006 [P] 创建 ContactSync Pydantic 模型 in src/models/message_schema.py
- [X] T007 [P] 创建 ProcessingCheckpoint 数据类 in src/models/checkpoint.py
- [X] T008 [P] 定义 MESSAGE_CONTENT_SCHEMA (PyArrow) in src/models/parquet_schemas.py
- [X] T009 [P] 定义 CONTACT_SYNC_SCHEMA (PyArrow) in src/models/parquet_schemas.py

### 基础工具函数

- [X] T010 [P] 实现 AtomicWriter 原子写入包装器 in src/lib/atomic_io.py
- [X] T011 [P] 实现 file_lock 上下文管理器 in src/lib/file_lock.py
- [X] T012 [P] 实现 Parquet Schema 工具函数 in src/lib/parquet_utils.py

### 检查点管理

- [X] T013 实现 CheckpointManager in src/services/storage/checkpoint.py

**Checkpoint**: 基础设施就绪 - 用户故事实现可以并行开始

---

## Phase 3: 用户故事 1 - 持久化消息到结构化存储 (优先级: P1) 🎯 MVP ✅ COMPLETED

**目标**: 将 webhook 日志转换为 Parquet 结构化存储,支持高效查询

**独立测试**: 运行存储管道处理现有 webhook 日志,验证 Parquet 文件创建正确且无数据丢失

### 契约测试 for US1

> **注意: 先写测试,确保失败后再实现**

- [X] T014 [P] [US1] MessageContent Schema 契约测试 in tests/contract/test_message_schema.py
- [X] T015 [P] [US1] JSONL 写入器契约测试 in tests/contract/test_jsonl_writer.py
- [X] T016 [P] [US1] Parquet 转换器契约测试 in tests/contract/test_parquet_converter.py

### JSONL 写入实现 for US1

- [X] T017 [P] [US1] 实现 JSONLWriter.append_message in src/services/storage/jsonl_writer.py
- [X] T018 [P] [US1] 实现 JSONLWriter.append_batch in src/services/storage/jsonl_writer.py
- [X] T019 [US1] 集成 JSONLWriter 到 webhook handler in src/endpoints/wechat/webhook_handler.py

### Parquet 转换实现 for US1

- [X] T020 [P] [US1] 实现 read_jsonl_stream 流式读取 in src/services/storage/jsonl_reader.py
- [X] T021 [US1] 实现 JSONLToParquetConverter.convert_to_parquet in src/services/storage/ingestion.py
- [X] T022 [US1] 实现字段类型归一化 (source: int→str) in src/services/storage/data_cleaner.py
- [X] T023 [US1] 实现分区字段提取 (year/month/day) in src/services/storage/partition.py
- [X] T024 [US1] 实现 BatchConverter.convert_all 批量转换 in src/services/storage/batch_converter.py

### 单元测试 for US1

- [X] T025 [P] [US1] JSONLWriter 单元测试 in tests/unit/test_jsonl_writer.py
- [X] T026 [P] [US1] JSONLToParquetConverter 单元测试 in tests/unit/test_ingestion.py
- [X] T027 [P] [US1] 分区逻辑单元测试 in tests/unit/test_partition.py

### 集成测试 for US1

- [X] T028 [US1] 端到端存储管道集成测试 in tests/integration/test_storage_pipeline.py
- [X] T029 [US1] 性能测试: 23,210条消息<5分钟 in tests/integration/test_performance.py

**Checkpoint**: 用户故事1完全功能化,可独立测试。验收场景1-4应全部通过。✅

---

## Phase 4: 用户故事 2 - 高效查询历史消息 (优先级: P2)

**目标**: 按日期、发送者、聊天室、消息类型查询历史消息

**独立测试**: 对存储数据运行预定义查询,测量性能和结果准确性

### 契约测试 for US2

- [ ] T030 [P] [US2] query_messages 契约测试 in tests/contract/test_query_api.py
- [ ] T031 [P] [US2] query_messages_by_id 契约测试 in tests/contract/test_query_api.py

### 查询实现 for US2

- [ ] T032 [P] [US2] 实现 query_messages (日期范围查询) in src/services/storage/query.py
- [ ] T033 [P] [US2] 实现 query_messages_by_id (ID查询) in src/services/storage/query.py
- [ ] T034 [US2] 实现分区裁剪逻辑 in src/services/storage/query_optimizer.py
- [ ] T035 [US2] 实现谓词下推过滤 in src/services/storage/query_optimizer.py
- [ ] T036 [US2] 实现列裁剪优化 in src/services/storage/query_optimizer.py

### CLI 命令 for US2

- [ ] T037 [US2] 实现 storage query CLI 命令 in src/cli/storage_commands.py

### 单元测试 for US2

- [ ] T038 [P] [US2] query_messages 单元测试 in tests/unit/test_query.py
- [ ] T039 [P] [US2] 查询优化器单元测试 in tests/unit/test_query_optimizer.py

### 集成测试 for US2

- [ ] T040 [US2] 查询性能集成测试 (单日<1秒, 月度<5秒) in tests/integration/test_query_performance.py
- [ ] T041 [US2] 多条件过滤集成测试 in tests/integration/test_query_filters.py

**Checkpoint**: 用户故事2完全功能化,可独立测试。验收场景1-4应全部通过。

---

## Phase 5: 用户故事 3 - 维护数据质量和完整性 (优先级: P2)

**目标**: 验证数据质量,处理 schema 演化,支持去重

**独立测试**: 引入格式错误消息和 schema 变更,验证系统优雅处理

### 契约测试 for US3

- [ ] T042 [P] [US3] validate_partition 契约测试 in tests/contract/test_validation_api.py
- [ ] T043 [P] [US3] detect_duplicates 契约测试 in tests/contract/test_validation_api.py

### 数据验证实现 for US3

- [ ] T044 [P] [US3] 实现 validate_partition (分区完整性检查) in src/services/storage/validation.py
- [ ] T045 [P] [US3] 实现 detect_duplicates (重复检测) in src/services/storage/validation.py
- [ ] T046 [P] [US3] 实现 validate_schema (Schema 验证) in src/services/storage/validation.py
- [ ] T047 [US3] 实现 SchemaRegistry (Schema 版本管理) in src/services/storage/schema_registry.py

### 去重实现 for US3

- [ ] T048 [US3] 实现 deduplicate_messages (基于 msg_id) in src/services/storage/deduplication.py
- [ ] T049 [US3] 实现 incremental_ingest (增量摄入+去重) in src/services/storage/incremental.py

### 错误处理 for US3

- [ ] T050 [US3] 实现格式错误消息跳过逻辑 in src/services/storage/error_handler.py
- [ ] T051 [US3] 实现 Schema 不兼容检测 in src/services/storage/schema_compat.py

### CLI 命令 for US3

- [ ] T052 [P] [US3] 实现 storage validate CLI 命令 in src/cli/storage_commands.py
- [ ] T053 [P] [US3] 实现 storage detect-duplicates CLI 命令 in src/cli/storage_commands.py

### 单元测试 for US3

- [ ] T054 [P] [US3] 数据验证单元测试 in tests/unit/test_validation.py
- [ ] T055 [P] [US3] 去重逻辑单元测试 in tests/unit/test_deduplication.py
- [ ] T056 [P] [US3] Schema 演化单元测试 in tests/unit/test_schema_evolution.py

### 集成测试 for US3

- [ ] T057 [US3] 格式错误处理集成测试 in tests/integration/test_error_handling.py
- [ ] T058 [US3] Schema 变更集成测试 in tests/integration/test_schema_evolution.py
- [ ] T059 [US3] 重复消息去重集成测试 in tests/integration/test_deduplication.py

**Checkpoint**: 用户故事3完全功能化,可独立测试。验收场景1-4应全部通过。

---

## Phase 6: 用户故事 4 - 归档和管理存储增长 (优先级: P3)

**目标**: 通过分区和归档管理存储增长,保持高性能

**独立测试**: 模拟数月数据,验证分区和归档功能

### 契约测试 for US4

- [ ] T060 [P] [US4] archive_old_partitions 契约测试 in tests/contract/test_archive_api.py
- [ ] T061 [P] [US4] cleanup_old_jsonl 契约测试 in tests/contract/test_archive_api.py

### 归档实现 for US4

- [ ] T062 [P] [US4] 实现 archive_old_partitions (Zstd-19压缩) in src/services/storage/archive.py
- [ ] T063 [P] [US4] 实现 cleanup_old_jsonl (JSONL清理) in src/services/storage/cleanup.py
- [ ] T064 [US4] 实现分区元数据管理 (StoragePartition) in src/services/storage/partition_metadata.py
- [ ] T065 [US4] 实现存储使用统计 in src/services/storage/storage_stats.py

### 定时任务实现 for US4

- [ ] T066 [US4] 创建 Systemd service 文件 in deploy/diting-parquet-dump.service
- [ ] T067 [US4] 创建 Systemd timer 文件 in deploy/diting-parquet-dump.timer

### CLI 命令 for US4

- [ ] T068 [P] [US4] 实现 storage dump-parquet CLI 命令 in src/cli/storage_commands.py
- [ ] T069 [P] [US4] 实现 storage cleanup CLI 命令 in src/cli/storage_commands.py
- [ ] T070 [P] [US4] 实现 storage archive CLI 命令 in src/cli/storage_commands.py

### 单元测试 for US4

- [ ] T071 [P] [US4] 归档逻辑单元测试 in tests/unit/test_archive.py
- [ ] T072 [P] [US4] 清理逻辑单元测试 in tests/unit/test_cleanup.py
- [ ] T073 [P] [US4] 分区元数据单元测试 in tests/unit/test_partition_metadata.py

### 集成测试 for US4

- [ ] T074 [US4] 归档流程集成测试 (90天数据) in tests/integration/test_archive_flow.py
- [ ] T075 [US4] JSONL清理集成测试 (7天保留) in tests/integration/test_cleanup_flow.py
- [ ] T076 [US4] 分区查询性能测试 (最近7天) in tests/integration/test_partition_query.py

**Checkpoint**: 用户故事4完全功能化,可独立测试。验收场景1-4应全部通过。

---

## Phase 7: Polish & Cross-Cutting Concerns

**目的**: 影响多个用户故事的改进

- [ ] T077 [P] 更新 README.md 添加存储功能说明
- [ ] T078 [P] 验证 quickstart.md 中的所有示例可运行
- [ ] T079 [P] 生成测试覆盖率报告,确保 ≥80%
- [ ] T080 代码质量检查 (ruff check, ruff format, mypy)
- [ ] T081 [P] 性能优化: 批量大小调优
- [ ] T082 [P] 安全审计: 敏感字段脱敏验证
- [ ] T083 添加性能监控日志 (处理时间、记录数、压缩率)
- [ ] T084 集成到 CI/CD pipeline (GitHub Actions)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成 - **阻塞所有用户故事**
- **用户故事 (Phase 3-6)**: 全部依赖 Foundational 完成
  - 用户故事可并行进行 (如有人员)
  - 或按优先级顺序进行 (P1 → P2 → P3)
- **Polish (Phase 7)**: 依赖所有期望的用户故事完成

### User Story Dependencies

- **用户故事 1 (P1)**: Foundational 后可开始 - 无其他故事依赖
- **用户故事 2 (P2)**: Foundational 后可开始 - 依赖 US1 (需要存储的数据进行查询)
- **用户故事 3 (P2)**: Foundational 后可开始 - 依赖 US1 (需要存储管道进行验证)
- **用户故事 4 (P3)**: Foundational 后可开始 - 依赖 US1 和 US2 (需要分区数据进行归档)

### Within Each User Story

- 契约测试必须先写并失败,然后再实现
- 模型 → 服务 → CLI命令
- 核心实现 → 集成
- 故事完成后再进入下一优先级

### Parallel Opportunities

- **Setup**: T003, T004 可并行
- **Foundational**: T005-T012 可并行执行
- **US1 契约测试**: T014, T015, T016 可并行
- **US1 JSONL写入**: T017, T018 可并行
- **US1 Parquet转换**: T020, T022, T023 可并行
- **US1 单元测试**: T025, T026, T027 可并行
- **US2 契约测试**: T030, T031 可并行
- **US2 查询实现**: T032, T033 可并行
- **US2 单元测试**: T038, T039 可并行
- **US3 契约测试**: T042, T043 可并行
- **US3 验证实现**: T044, T045, T046 可并行
- **US3 CLI命令**: T052, T053 可并行
- **US3 单元测试**: T054, T055, T056 可并行
- **US4 契约测试**: T060, T061 可并行
- **US4 归档实现**: T062, T063 可并行
- **US4 CLI命令**: T068, T069, T070 可并行
- **US4 单元测试**: T071, T072, T073 可并行
- **Polish**: T077, T078, T079, T081, T082 可并行

---

## Parallel Example: 用户故事 1

```bash
# 并行启动 US1 的所有契约测试:
Task: "MessageContent Schema 契约测试 in tests/contract/test_message_schema.py"
Task: "JSONL 写入器契约测试 in tests/contract/test_jsonl_writer.py"
Task: "Parquet 转换器契约测试 in tests/contract/test_parquet_converter.py"

# 并行启动 US1 的 JSONL 写入实现:
Task: "实现 JSONLWriter.append_message in src/services/storage/jsonl_writer.py"
Task: "实现 JSONLWriter.append_batch in src/services/storage/jsonl_writer.py"

# 并行启动 US1 的单元测试:
Task: "JSONLWriter 单元测试 in tests/unit/test_jsonl_writer.py"
Task: "JSONLToParquetConverter 单元测试 in tests/unit/test_ingestion.py"
Task: "分区逻辑单元测试 in tests/unit/test_partition.py"
```

---

## Implementation Strategy

### MVP First (仅用户故事 1)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational (**关键 - 阻塞所有故事**)
3. 完成 Phase 3: 用户故事 1
4. **停止并验证**: 独立测试用户故事 1
5. 如准备好则部署/演示

### Incremental Delivery

1. 完成 Setup + Foundational → 基础就绪
2. 添加用户故事 1 → 独立测试 → 部署/演示 (MVP!)
3. 添加用户故事 2 → 独立测试 → 部署/演示
4. 添加用户故事 3 → 独立测试 → 部署/演示
5. 添加用户故事 4 → 独立测试 → 部署/演示
6. 每个故事增加价值而不破坏之前的故事

### Parallel Team Strategy

多个开发者情况下:

1. 团队共同完成 Setup + Foundational
2. Foundational 完成后:
   - 开发者 A: 用户故事 1
   - 开发者 B: 用户故事 2 (等待 US1 完成后开始)
   - 开发者 C: 用户故事 3 (等待 US1 完成后开始)
   - 开发者 D: 用户故事 4 (等待 US1, US2 完成后开始)
3. 故事独立完成和集成

---

## Task Summary

- **总任务数**: 84
- **用户故事 1 (P1)**: 16 个任务 (T014-T029)
- **用户故事 2 (P2)**: 12 个任务 (T030-T041)
- **用户故事 3 (P2)**: 18 个任务 (T042-T059)
- **用户故事 4 (P3)**: 17 个任务 (T060-T076)
- **Setup + Foundational**: 13 个任务 (T001-T013)
- **Polish**: 8 个任务 (T077-T084)

### 并行机会统计

- **Setup阶段**: 2 个并行组
- **Foundational阶段**: 8 个并行任务
- **US1**: 7 个并行组
- **US2**: 4 个并行组
- **US3**: 7 个并行组
- **US4**: 7 个并行组
- **Polish**: 5 个并行任务

### MVP 范围建议

推荐 MVP 包含:
- Phase 1: Setup (4 个任务)
- Phase 2: Foundational (9 个任务)
- Phase 3: 用户故事 1 (16 个任务)
- **MVP 总计**: 29 个任务

这将提供核心价值: 将 webhook 日志持久化为 Parquet 格式并支持基本查询。

---

## Notes

- [P] 任务 = 不同文件,无依赖
- [Story] 标签将任务映射到特定用户故事以便追溯
- 每个用户故事应可独立完成和测试
- 先验证测试失败再实现
- 每个任务或逻辑组完成后提交
- 在任何检查点停止以独立验证故事
- 避免: 模糊任务, 同文件冲突, 破坏独立性的跨故事依赖
