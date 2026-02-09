# 元数据存储架构设计

## 背景

diting 项目是一个微信消息分析系统，当前使用 DuckDB + Parquet 作为主要存储方案。随着数据量增长（图片元数据已达 1.1GB），需要更好的元数据管理方案来管理：

- Schema 版本历史（当前用 JSON 文件）
- 分区元数据（当前实时扫描）
- 处理检查点（当前用 JSON 文件）
- 任务调度状态
- 数据质量指标
- 数据血缘关系

## 当前架构

| 数据类型 | 存储方式 | 位置 |
|---------|---------|------|
| 消息数据 | Parquet (year/month/day 分区) | `data/messages/parquet/` |
| 图片元数据 | DuckDB (1.1GB) | `data/metadata/images.duckdb` |
| Schema 版本 | JSON 文件 | `data/metadata/schema_registry.json` |
| 检查点 | JSON 文件 | `data/metadata/checkpoints/*.json` |

## 技术选型：SQLite vs PostgreSQL

### SQLite

| 优势 | 劣势 |
|-----|------|
| 零配置部署，单文件数据库 | 写锁是数据库级别 |
| Python 标准库原生支持 | 无存储过程 |
| 与 DuckDB 部署模式一致 | JSON 支持不如 PostgreSQL |
| 内存占用极低 | 无高级索引类型 |
| ACID 完整支持 + WAL 模式 | |

### PostgreSQL

| 优势 | 劣势 |
|-----|------|
| 企业级功能（高级索引、JSONB） | 需要安装和配置服务 |
| MVCC 高并发读写 | 内存占用高（512MB+） |
| 主从复制、分区表 | 需要持续运行后台进程 |
| 丰富的监控和备份工具 | 运维成本高 |

### 决策：选择 SQLite

| 考量因素 | 分析 | 结论 |
|---------|------|------|
| 项目规模 | 单机部署，数据量 GB 级 | SQLite 足够 |
| 并发需求 | 单进程 CLI + 单 FastAPI 服务 | SQLite 足够 |
| 运维能力 | 个人/小团队项目 | 简化运维优先 |
| 架构一致性 | 已有 DuckDB 嵌入式方案 | 保持一致 |
| 未来扩展 | 可随时迁移到 PostgreSQL | 不阻塞 |

**SQLite 与 DuckDB 的关系**：互补而非冗余

- DuckDB：OLAP（分析查询），适合大数据扫描、与 Parquet 联合查询
- SQLite：OLTP（事务处理），适合小数据 CRUD、系统元数据

## 图片元数据存储位置分析

### 现状：DuckDB 被当作 SQLite 在用

通过代码审查发现，`images.duckdb`（1.1GB）中的图片元数据**完全是 OLTP 操作**：

| 操作 | 代码位置 | 模式 |
|-----|---------|------|
| 批量插入 | `image_repository.py:96` | 逐条 INSERT + 去重检查 |
| 按 status 查询 | `image_repository.py:146` | `WHERE status = ? LIMIT ?` |
| 按 image_id 查询 | `image_repository.py:170` | `WHERE image_id = ?` |
| 按 msg_id 查询 | `image_repository.py:194` | `WHERE msg_id = ?` |
| 更新状态 | `image_repository.py:218` | `UPDATE ... WHERE image_id = ?` |
| 待 OCR 查询 | `image_repository.py:252` | `WHERE ... IS NOT NULL AND ... IS NULL` |
| 更新 OCR 结果 | `image_repository.py:280` | `UPDATE ... WHERE image_id = ?` |
| COUNT 统计 | `statistics_repository.py:30` | `SELECT COUNT(*) ... WHERE status = ?` |

**关键发现**：
1. **没有使用 DuckDB 的 OLAP 特性**：无 `read_parquet`、无向量化查询、无与 Parquet 联合查询
2. **所有操作都是纯 OLTP**：单条插入、按索引查询、单条更新
3. **DuckDB 的 OLAP 优势完全没有被利用**

### 建议：将图片元数据迁移到 SQLite

**迁移理由**：

| 因素 | DuckDB | SQLite |
|-----|--------|--------|
| OLTP 性能 | 一般（OLAP 优化） | 优秀（OLTP 优化） |
| 并发写入 | 单写者限制 | WAL 模式支持并发读 |
| 连接开销 | 每次操作新建连接 | 轻量连接 |
| 依赖 | 需要 `duckdb` 包 | Python 标准库 |
| 文件大小 | 1.1GB（OLAP 存储格式） | 预计更小（OLTP 优化） |
| 统一管理 | 独立数据库文件 | 与其他元数据统一 |

**迁移后的好处**：
1. 消除 DuckDB 依赖（如果不再需要 DuckDB 的 OLAP 功能）
2. 所有元数据统一在一个 SQLite 文件中管理
3. OLTP 查询性能提升
4. 减少存储空间

**保留 DuckDB 的场景**：
- 如果未来需要 DuckDB 直接查询 Parquet 文件（如 `SELECT * FROM read_parquet('data/messages/parquet/**/*.parquet')`）
- 如果需要对图片元数据做大规模分析查询

### 建议方案

**推荐**：将图片元数据迁移到 SQLite，统一所有元数据管理。保留 DuckDB 作为可选的分析查询引擎（按需加载，不作为持久化存储）。

## SQLite 并发读写方案

### 当前项目并发现状

通过代码审查，项目当前的并发模式如下：

| 组件 | 并发模型 | 数据库访问 |
|-----|---------|-----------|
| FastAPI webhook | 单 worker，async I/O | 仅写 JSONL（文件锁保护） |
| CLI download-images | 串行下载 | 读写 DuckDB |
| CLI process-ocr | 串行处理 | 读写 DuckDB |
| CLI extract-images | 串行提取 | 读写 DuckDB |
| CLI analyze | 串行批次 | 读 DuckDB |
| 数据摄入 | 串行写入 | 不访问 DuckDB |

**关键发现**：
1. 所有 CLI 命令都是**串行处理**，没有使用线程池或进程池
2. FastAPI 服务**不直接访问** DuckDB，仅写 JSONL
3. DuckDB 连接是**每次操作新建、用完关闭**，没有连接池
4. 可能的并发场景：多个 CLI 命令在不同终端同时运行

### SQLite 并发策略

#### WAL 模式（Write-Ahead Logging）

```python
conn.execute("PRAGMA journal_mode=WAL")
```

WAL 模式下的并发能力：
- **多读者 + 单写者**：多个连接可以同时读取，写入不阻塞读取
- **写入排队**：多个写入请求自动排队，SQLite 内部处理锁
- **默认超时**：写入等待锁的默认超时为 5 秒

#### 连接管理策略

```python
import sqlite3
import threading
from contextlib import contextmanager

class SQLiteConnection:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._local = threading.local()

    @contextmanager
    def get_connection(self):
        # 每个线程使用独立连接
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                timeout=30,  # 写入等待锁超时 30 秒
                check_same_thread=False,
            )
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=30000")
            self._local.conn.row_factory = sqlite3.Row
        try:
            yield self._local.conn
            self._local.conn.commit()
        except Exception:
            self._local.conn.rollback()
            raise
```

#### 多进程安全

SQLite WAL 模式天然支持多进程访问同一数据库文件：

```
进程 1: diting download-images
  └─> SQLite WAL: 读写 images 表 ✅

进程 2: diting process-ocr
  └─> SQLite WAL: 读写 images 表 ✅

进程 3: diting analyze
  └─> SQLite WAL: 只读 images 表 ✅
```

关键配置：
- `PRAGMA busy_timeout=30000`：写入冲突时等待 30 秒而非立即失败
- `PRAGMA journal_mode=WAL`：允许并发读写
- `PRAGMA wal_autocheckpoint=1000`：每 1000 页自动 checkpoint

#### 与当前 DuckDB 对比

| 并发特性 | DuckDB（当前） | SQLite WAL |
|---------|---------------|------------|
| 多进程读 | 支持 | 支持 |
| 多进程写 | 单写者，其他阻塞 | 单写者，其他排队等待 |
| 写入超时 | 无配置 | `busy_timeout` 可配置 |
| 读写并发 | 写阻塞读 | 写不阻塞读 |
| 连接模型 | 每次新建 | 可复用（线程本地） |

**结论**：SQLite WAL 模式的并发能力**优于**当前 DuckDB 的使用方式，完全满足项目需求。

## 目标架构

```
┌──────────────────────────────────────────────────────────────┐
│                      diting 存储架构                          │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐    ┌────────────────────────────┐  │
│  │   SQLite             │    │   Parquet                  │  │
│  │   (所有元数据)        │    │   (消息数据)                │  │
│  │                      │    │                            │  │
│  │  - images            │    │  year=2026/                │  │
│  │  - image_checkpoints │    │    month=01/               │  │
│  │  - schema_versions   │    │      day=23/               │  │
│  │  - partitions        │    │        part-0.parquet      │  │
│  │  - checkpoints       │    │        part-1.parquet      │  │
│  │  - tasks             │    │                            │  │
│  │  - data_quality      │    │                            │  │
│  │  - lineage           │    │                            │  │
│  └──────────────────────┘    └────────────────────────────┘  │
│                                                              │
│  文件位置:                                                    │
│  data/metadata/diting.sqlite     data/messages/parquet/      │
│                                                              │
│  可选 (按需分析):                                             │
│  DuckDB 作为查询引擎直接读取 Parquet，不作为持久化存储          │
└──────────────────────────────────────────────────────────────┘
```

## SQLite 表设计

### 1. 图片元数据

从 DuckDB 迁移，保持相同的表结构和索引。

```sql
CREATE TABLE images (
    image_id TEXT PRIMARY KEY,
    msg_id TEXT NOT NULL UNIQUE,
    from_username TEXT NOT NULL,
    create_time TIMESTAMP,
    aes_key TEXT NOT NULL,
    cdn_mid_img_url TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    download_url TEXT,
    error_message TEXT,
    ocr_content TEXT,
    has_text INTEGER,  -- SQLite 无 BOOLEAN，用 0/1
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    downloaded_at TIMESTAMP
);

CREATE INDEX idx_images_status ON images(status);
CREATE INDEX idx_images_from_username ON images(from_username);
CREATE INDEX idx_images_msg_id ON images(msg_id);
```

### 2. 图片提取检查点

从 DuckDB 迁移。

```sql
CREATE TABLE image_extraction_checkpoints (
    parquet_file TEXT PRIMARY KEY,
    from_username TEXT NOT NULL,
    total_images_extracted INTEGER DEFAULT 0,
    status TEXT DEFAULT 'processing',
    checkpoint_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

CREATE INDEX idx_img_checkpoints_status ON image_extraction_checkpoints(status);
```

### 3. Schema 版本管理

替代现有的 `schema_registry.json`。

```sql
CREATE TABLE schema_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_name TEXT NOT NULL,
    version INTEGER NOT NULL,
    schema_json TEXT NOT NULL,  -- PyArrow schema 序列化
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(schema_name, version)
);

CREATE INDEX idx_schema_name ON schema_versions(schema_name);
```

### 4. 分区元数据

替代现有的实时扫描逻辑，缓存分区统计信息。

```sql
CREATE TABLE partitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partition_key TEXT NOT NULL UNIQUE,  -- year=2026/month=01/day=23
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    file_count INTEGER DEFAULT 0,
    row_count INTEGER DEFAULT 0,
    size_bytes INTEGER DEFAULT 0,
    min_timestamp INTEGER,
    max_timestamp INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_partitions_date ON partitions(year, month, day);
```

### 5. 处理检查点

替代现有的 `checkpoints/*.json` 文件。

```sql
CREATE TABLE checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL UNIQUE,
    checkpoint_type TEXT NOT NULL,  -- 'ingestion', 'image_extraction', 'analysis'
    last_processed_line INTEGER DEFAULT 0,
    last_processed_msg_id TEXT,
    last_processed_timestamp INTEGER,
    processed_record_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_checkpoints_status ON checkpoints(status);
CREATE INDEX idx_checkpoints_type ON checkpoints(checkpoint_type);
```

### 6. 任务调度状态

新增功能，用于跟踪后台任务执行状态。

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    task_type TEXT NOT NULL,  -- 'daily_analysis', 'image_download', 'ocr_process'
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
    result_json TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_scheduled ON tasks(scheduled_at);
CREATE INDEX idx_tasks_type ON tasks(task_type);
```

### 7. 数据质量指标

新增功能，用于跟踪数据质量。

```sql
CREATE TABLE data_quality_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partition_key TEXT NOT NULL,
    metric_name TEXT NOT NULL,  -- 'null_rate', 'duplicate_rate', 'schema_violations'
    metric_value REAL NOT NULL,
    details_json TEXT,
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(partition_key, metric_name, measured_at)
);

CREATE INDEX idx_quality_partition ON data_quality_metrics(partition_key);
CREATE INDEX idx_quality_metric ON data_quality_metrics(metric_name);
```

### 8. 数据血缘

新增功能，用于跟踪数据流转关系。

```sql
CREATE TABLE data_lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,  -- 'jsonl', 'parquet', 'duckdb'
    source_path TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_path TEXT NOT NULL,
    operation TEXT NOT NULL,  -- 'ingest', 'transform', 'extract'
    record_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lineage_source ON data_lineage(source_path);
CREATE INDEX idx_lineage_target ON data_lineage(target_path);
CREATE INDEX idx_lineage_operation ON data_lineage(operation);
```

## 实施计划

### Phase 1: 创建 SQLite 基础设施

1. 创建 `src/diting/services/storage/sqlite_base.py` - 连接管理（WAL 模式、外键约束）
2. 创建 `src/diting/services/storage/sqlite_manager.py` - Facade 管理器
3. 实现表初始化（所有 8 张表）
4. 添加单元测试

### Phase 2: 迁移图片元数据（DuckDB → SQLite）

1. 在 SQLite 中创建 `images` 和 `image_extraction_checkpoints` 表
2. 重写 `ImageRepository`、`CheckpointRepository`、`StatisticsRepository` 使用 SQLite
3. 保持 `DuckDBManager` 的公共 API 不变（改名为 `SQLiteManager`）
4. 编写 DuckDB → SQLite 数据迁移脚本
5. 更新所有调用方（CLI、image_extractor、image_downloader、image_ocr_processor、analysis）
6. 添加迁移测试

### Phase 3: 迁移 Schema Registry（JSON → SQLite）

1. 修改 `SchemaRegistry` 类，使用 SQLite 后端
2. 保持公共 API 不变
3. 添加 JSON → SQLite 迁移脚本

### Phase 4: 迁移检查点（JSON → SQLite）

1. 从 JSON 文件迁移到 SQLite
2. 保持现有接口不变
3. 添加迁移脚本

### Phase 5: 新增元数据功能

1. 实现分区元数据缓存
2. 实现任务调度状态跟踪
3. 实现数据质量指标收集
4. 实现数据血缘记录

### Phase 6: 清理

1. 移除 DuckDB 依赖（如果不再需要）
2. 删除旧的 JSON 文件和 DuckDB 文件
3. 更新文档和配置

## 关键文件

| 文件 | 说明 | 变更 |
|-----|------|------|
| `src/diting/services/storage/duckdb_base.py` | DuckDB 连接管理 | 替换为 sqlite_base.py |
| `src/diting/services/storage/duckdb_manager.py` | DuckDB Facade | 替换为 sqlite_manager.py |
| `src/diting/services/storage/image_repository.py` | 图片数据仓库 | 改用 SQLite |
| `src/diting/services/storage/checkpoint_repository.py` | 检查点仓库 | 改用 SQLite |
| `src/diting/services/storage/statistics_repository.py` | 统计仓库 | 改用 SQLite |
| `src/diting/services/storage/schema_registry.py` | Schema 注册（JSON） | 改用 SQLite |
| `src/diting/services/storage/partition_metadata.py` | 分区元数据 | 改用 SQLite 缓存 |
| `src/diting/services/storage/image_extractor.py` | 图片提取 | 更新 DuckDBManager 引用 |
| `src/diting/services/storage/image_downloader.py` | 图片下载 | 更新 DuckDBManager 引用 |
| `src/diting/services/storage/image_ocr_processor.py` | OCR 处理 | 更新 DuckDBManager 引用 |
| `src/diting/services/llm/analysis.py` | LLM 分析 | 更新 DuckDBManager 引用 |
| `src/diting/services/llm/message_formatter.py` | 消息格式化 | 更新 DuckDBManager 引用 |
| `src/diting/cli/main.py` | CLI 入口 | 更新数据库路径和引用 |
| `src/diting/config.py` | 配置管理 | 添加 SQLite 路径配置 |

## 验证方式

1. **单元测试**：SQLite 管理器的 CRUD 操作
2. **集成测试**：与现有 DuckDB 的协作
3. **迁移测试**：JSON → SQLite 数据迁移正确性
4. **性能测试**：查询性能对比

## 未来扩展

如果未来需要迁移到 PostgreSQL，可以：

1. 保持相同的表结构
2. 使用 SQLAlchemy 抽象数据库访问
3. 通过配置切换数据库后端
