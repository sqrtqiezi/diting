# 存储服务 API 契约

**版本**: 1.0.0
**功能**: 006-wechat-message-storage
**类型**: Python API (非 REST)

## 概述

本契约定义微信消息数据湖存储服务的 Python API 接口,包括摄入、查询、验证和归档功能。

---

## 1. 摄入服务 (Ingestion Service)

### 1.1 append_message_to_jsonl

追加单条消息到当日 JSONL 文件。

#### 签名

```python
def append_message_to_jsonl(
    message: dict[str, Any],
    base_dir: str | Path = "data/messages/raw"
) -> None
```

#### 输入

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `message` | dict | ✅ | 消息数据字典 |
| `base_dir` | str/Path | ❌ | JSONL 文件基础目录 |

#### 输出

- **成功**: None (静默成功)
- **失败**: 抛出 `OSError` 或 `ValueError`

#### 行为

- 获取当前日期(UTC),确定文件名 `YYYY-MM-DD.jsonl`
- 使用文件锁(`portalocker`)获取排他锁
- 追加 JSON 行到文件末尾
- 刷新缓冲区并执行 `fsync`
- 释放文件锁

#### 错误码

| 错误类型 | 条件 | 处理 |
|---------|------|------|
| `OSError` | 文件写入失败或锁超时 | 记录错误日志,抛出异常 |
| `ValueError` | JSON 序列化失败 | 记录错误日志,抛出异常 |

#### 示例

```python
from diting.services.storage import append_message_to_jsonl

message = {
    "msg_id": "1234567890",
    "from_username": "wxid_abc123",
    "content": "Hello World",
    "create_time": 1737590400
}

append_message_to_jsonl(message)
# 结果: 消息追加到 data/messages/raw/2026-01-23.jsonl
```

---

### 1.2 convert_jsonl_to_parquet

转换 JSONL 文件到 Parquet 分区数据集。

#### 签名

```python
def convert_jsonl_to_parquet(
    jsonl_path: str | Path,
    parquet_root: str | Path,
    schema: pa.Schema | None = None,
    compression: str = "snappy",
    batch_size: int = 10_000
) -> dict[str, Any]
```

#### 输入

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `jsonl_path` | str/Path | ✅ | - | 源 JSONL 文件路径 |
| `parquet_root` | str/Path | ✅ | - | Parquet 输出根目录 |
| `schema` | pa.Schema | ❌ | None | PyArrow Schema(None=自动推断) |
| `compression` | str | ❌ | `"snappy"` | 压缩算法(snappy/zstd/gzip) |
| `batch_size` | int | ❌ | 10000 | 每批处理的记录数 |

#### 输出

返回转换统计信息字典:

```python
{
    "source_file": str,          # 源文件路径
    "target_file": str,          # 目标 Parquet 路径
    "total_records": int,        # 总记录数
    "total_batches": int,        # 批次数
    "source_size_mb": float,     # 源文件大小(MB)
    "target_size_mb": float,     # 目标文件大小(MB)
    "compression_ratio": float   # 压缩率
}
```

#### 行为

1. 流式读取 JSONL 文件(逐行解析)
2. 累积记录到批次(默认 10,000 条)
3. 转换批次为 PyArrow Table
4. 写入 Parquet 文件(带压缩)
5. 返回统计信息

#### 错误码

| 错误类型 | 条件 | 处理 |
|---------|------|------|
| `FileNotFoundError` | JSONL 文件不存在 | 抛出异常 |
| `json.JSONDecodeError` | JSON 解析失败 | 跳过错误行,记录警告 |
| `OSError` | Parquet 写入失败 | 删除不完整文件,抛出异常 |

#### 示例

```python
from diting.services.storage import convert_jsonl_to_parquet

stats = convert_jsonl_to_parquet(
    jsonl_path="data/messages/raw/2026-01-23.jsonl",
    parquet_root="data/parquet/messages",
    compression="snappy"
)

print(stats)
# {
#     "source_file": "data/messages/raw/2026-01-23.jsonl",
#     "target_file": "data/parquet/messages/year=2026/month=01/day=23/data.parquet",
#     "total_records": 1523,
#     "total_batches": 1,
#     "source_size_mb": 15.2,
#     "target_size_mb": 7.8,
#     "compression_ratio": 1.95
# }
```

---

### 1.3 incremental_ingest

增量摄取 JSONL 到 Parquet(带检查点)。

#### 签名

```python
def incremental_ingest(
    source_jsonl: str | Path,
    parquet_root: str | Path,
    checkpoint_dir: str | Path = "data/metadata/checkpoints"
) -> dict[str, Any]
```

#### 输入

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `source_jsonl` | str/Path | ✅ | - | 源 JSONL 文件路径 |
| `parquet_root` | str/Path | ✅ | - | Parquet 输出根目录 |
| `checkpoint_dir` | str/Path | ❌ | `data/metadata/checkpoints` | 检查点存储目录 |

#### 输出

```python
{
    "new_records": int,          # 新增记录数
    "deduplicated": int,         # 去重后记录数
    "skipped_duplicates": int,   # 跳过的重复记录
    "checkpoint_updated": bool   # 检查点是否更新
}
```

#### 行为

1. 加载检查点(如存在)
2. 从上次处理位置继续读取
3. 去重(基于 `msg_id`)
4. 追加写入 Parquet
5. 更新检查点

#### 示例

```python
from diting.services.storage import incremental_ingest

result = incremental_ingest(
    source_jsonl="data/messages/raw/2026-01-23.jsonl",
    parquet_root="data/parquet/messages"
)

print(result)
# {
#     "new_records": 150,
#     "deduplicated": 148,
#     "skipped_duplicates": 2,
#     "checkpoint_updated": True
# }
```

---

## 2. 查询服务 (Query Service)

### 2.1 query_messages

查询消息记录(支持时间范围和过滤条件)。

#### 签名

```python
def query_messages(
    start_date: str,
    end_date: str,
    parquet_root: str | Path = "data/parquet/messages",
    filters: dict[str, Any] | None = None,
    columns: list[str] | None = None
) -> pd.DataFrame
```

#### 输入

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `start_date` | str | ✅ | - | 开始日期(YYYY-MM-DD) |
| `end_date` | str | ✅ | - | 结束日期(YYYY-MM-DD) |
| `parquet_root` | str/Path | ❌ | `data/parquet/messages` | Parquet 根目录 |
| `filters` | dict | ❌ | None | 额外过滤条件 |
| `columns` | list[str] | ❌ | None | 需要的列(None=全部) |

#### filters 格式

```python
{
    "chatroom": "chatroom_123",          # 群聊 ID
    "from_username": "wxid_abc",         # 发送者
    "msg_type": 1                        # 消息类型
}
```

#### 输出

返回 Pandas DataFrame,包含查询结果。

#### 行为

1. 解析日期范围,构建分区过滤器
2. 使用 PyArrow 谓词下推读取 Parquet
3. 精确过滤时间戳
4. 应用额外过滤条件
5. 返回 DataFrame

#### 性能指标

- **单日查询**: <1 秒
- **月度查询**: <5 秒

#### 示例

```python
from diting.services.storage import query_messages

# 查询 2026-01-20 到 2026-01-23 的所有消息
df = query_messages(
    start_date="2026-01-20",
    end_date="2026-01-23"
)

# 查询特定群聊的消息
df = query_messages(
    start_date="2026-01-20",
    end_date="2026-01-23",
    filters={"chatroom": "chatroom_123"},
    columns=["msg_id", "from_username", "content", "create_time"]
)

print(df.head())
```

---

### 2.2 query_messages_by_id

根据 msg_id 查询消息。

#### 签名

```python
def query_messages_by_id(
    msg_ids: list[str],
    parquet_root: str | Path = "data/parquet/messages"
) -> pd.DataFrame
```

#### 输入

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `msg_ids` | list[str] | ✅ | 消息 ID 列表 |
| `parquet_root` | str/Path | ❌ | Parquet 根目录 |

#### 输出

返回 Pandas DataFrame,包含匹配的消息。

#### 示例

```python
df = query_messages_by_id(
    msg_ids=["1234567890", "9876543210"]
)
```

---

## 3. 验证服务 (Validation Service)

### 3.1 validate_partition

验证 Parquet 分区的完整性。

#### 签名

```python
def validate_partition(
    partition_path: str | Path
) -> dict[str, Any]
```

#### 输入

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `partition_path` | str/Path | ✅ | 分区目录路径 |

#### 输出

```python
{
    "is_valid": bool,            # 分区是否有效
    "file_count": int,           # Parquet 文件数量
    "total_records": int,        # 总记录数
    "total_size_bytes": int,     # 总大小(字节)
    "errors": list[str]          # 错误列表
}
```

#### 验证规则

- ✅ 分区目录存在
- ✅ 至少包含一个 Parquet 文件
- ✅ 所有文件大小 >0
- ✅ Schema 一致性
- ✅ 无损坏文件

#### 示例

```python
result = validate_partition(
    "data/parquet/messages/year=2026/month=01/day=23"
)

print(result)
# {
#     "is_valid": True,
#     "file_count": 1,
#     "total_records": 1523,
#     "total_size_bytes": 8174592,
#     "errors": []
# }
```

---

### 3.2 detect_duplicates

检测 Parquet 数据集中的重复消息。

#### 签名

```python
def detect_duplicates(
    parquet_root: str | Path
) -> pd.DataFrame
```

#### 输入

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `parquet_root` | str/Path | ✅ | Parquet 根目录 |

#### 输出

返回包含重复 `msg_id` 及其出现次数的 DataFrame。

```python
# 示例输出
   msg_id         count
0  1234567890    2
1  9876543210    3
```

#### 示例

```python
duplicates = detect_duplicates("data/parquet/messages")
print(f"发现 {len(duplicates)} 个重复消息")
```

---

## 4. 归档服务 (Archive Service)

### 4.1 archive_old_partitions

归档旧分区(重新压缩为 Zstd-19)。

#### 签名

```python
def archive_old_partitions(
    parquet_root: str | Path,
    archive_root: str | Path,
    older_than_days: int = 90,
    compression: str = "zstd",
    compression_level: int = 19
) -> dict[str, Any]
```

#### 输入

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `parquet_root` | str/Path | ✅ | - | 源 Parquet 根目录 |
| `archive_root` | str/Path | ✅ | - | 归档目标目录 |
| `older_than_days` | int | ❌ | 90 | 归档阈值(天) |
| `compression` | str | ❌ | `"zstd"` | 压缩算法 |
| `compression_level` | int | ❌ | 19 | 压缩级别(1-22) |

#### 输出

```python
{
    "archived_partitions": int,      # 归档分区数
    "total_size_before_mb": float,   # 原始大小(MB)
    "total_size_after_mb": float,    # 归档后大小(MB)
    "compression_ratio": float       # 压缩率
}
```

#### 行为

1. 扫描分区,筛选超过阈值的分区
2. 重新压缩为 Zstd-19
3. 写入归档目录
4. 验证归档成功后删除原文件

#### 示例

```python
result = archive_old_partitions(
    parquet_root="data/parquet/messages",
    archive_root="data/archive/messages",
    older_than_days=90
)

print(result)
# {
#     "archived_partitions": 15,
#     "total_size_before_mb": 450.2,
#     "total_size_after_mb": 135.8,
#     "compression_ratio": 3.31
# }
```

---

### 4.2 cleanup_old_jsonl

清理过期的 JSONL 文件(7 天前)。

#### 签名

```python
def cleanup_old_jsonl(
    raw_dir: str | Path,
    parquet_root: str | Path,
    retention_days: int = 7,
    dry_run: bool = False
) -> dict[str, Any]
```

#### 输入

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `raw_dir` | str/Path | ✅ | - | JSONL 文件目录 |
| `parquet_root` | str/Path | ✅ | - | Parquet 根目录 |
| `retention_days` | int | ❌ | 7 | 保留天数 |
| `dry_run` | bool | ❌ | False | 试运行(不实际删除) |

#### 输出

```python
{
    "total_scanned": int,            # 扫描的文件数
    "deleted": int,                  # 删除的文件数
    "skipped_no_parquet": int,       # 跳过(Parquet 不存在)
    "skipped_in_use": int,           # 跳过(文件使用中)
    "deleted_files": list[str]       # 已删除文件列表
}
```

#### 安全检查

- ✅ 验证 Parquet 文件存在
- ✅ 检查文件是否被占用
- ✅ 验证文件日期 >7 天

#### 示例

```python
# 试运行
result = cleanup_old_jsonl(
    raw_dir="data/messages/raw",
    parquet_root="data/parquet/messages",
    dry_run=True
)

# 实际删除
result = cleanup_old_jsonl(
    raw_dir="data/messages/raw",
    parquet_root="data/parquet/messages"
)
```

---

## 5. 错误处理契约

### 通用错误类型

| 错误类 | HTTP 等价 | 描述 | 处理建议 |
|--------|----------|------|---------|
| `FileNotFoundError` | 404 | 文件不存在 | 检查路径,创建文件 |
| `PermissionError` | 403 | 权限不足 | 检查文件权限 |
| `OSError` | 500 | I/O 错误 | 检查磁盘空间,重试 |
| `ValueError` | 400 | 参数错误 | 验证输入参数 |
| `json.JSONDecodeError` | 422 | JSON 解析失败 | 检查数据格式 |

### 错误日志格式

所有错误使用 `structlog` 记录:

```python
logger.error(
    "operation_failed",
    operation="convert_jsonl_to_parquet",
    source_file="2026-01-23.jsonl",
    error=str(e),
    error_type=type(e).__name__
)
```

---

## 6. 性能契约

### 摄入性能

| 操作 | 数据量 | 目标时间 |
|------|--------|---------|
| `append_message_to_jsonl` | 1 条消息 | <10ms |
| `convert_jsonl_to_parquet` | 23,210 条消息(342MB) | <5 分钟 |
| `incremental_ingest` | 150 条新消息 | <1 分钟 |

### 查询性能

| 操作 | 数据范围 | 目标时间 |
|------|---------|---------|
| `query_messages` (单日) | 1 天数据 | <1 秒 |
| `query_messages` (月度) | 30 天数据 | <5 秒 |
| `query_messages_by_id` | 100 个 ID | <2 秒 |

### 内存使用

| 操作 | 峰值内存 |
|------|---------|
| `convert_jsonl_to_parquet` | <500MB |
| `query_messages` (单日) | <200MB |
| `query_messages` (月度) | <800MB |

---

## 7. 测试契约

### 单元测试要求

- ✅ 所有公开函数必须有单元测试
- ✅ 测试覆盖率 ≥80%
- ✅ Mock 外部依赖(文件系统、Parquet I/O)

### 集成测试要求

- ✅ 端到端摄入流程测试
- ✅ 查询性能测试
- ✅ 错误恢复测试(断点续传)

### 契约测试要求

- ✅ 验证 API 签名不变
- ✅ 验证输入/输出格式不变
- ✅ 验证错误码不变

---

## 8. 版本兼容性

### 语义化版本控制

API 遵循语义化版本控制 (SemVer):
- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 新增功能(向后兼容)
- **PATCH**: Bug 修复(向后兼容)

当前版本: **1.0.0**

### 废弃策略

- 废弃功能保留 2 个 MINOR 版本
- 使用 `@deprecated` 装饰器标记
- 提供迁移指南
