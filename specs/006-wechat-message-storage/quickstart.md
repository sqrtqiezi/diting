# 快速开始指南：微信消息数据湖存储

**功能分支**: `006-wechat-message-storage`
**前置条件**: Python 3.12.6, 虚拟环境已配置
**相关文档**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md)

## 概述

本指南帮助开发者快速上手微信消息数据湖存储系统,涵盖环境配置、基本用法和常见场景。

---

## 1. 环境准备

### 1.1 安装依赖

```bash
# 添加 Parquet 和文件锁依赖
uv add pyarrow portalocker

# 同步所有依赖
uv sync --frozen
```

### 1.2 验证安装

```bash
# 激活虚拟环境(uv 会自动管理)
uv run python -c "import pyarrow; print(pyarrow.__version__)"
# 预期输出: 14.x.x

uv run python -c "import portalocker; print('OK')"
# 预期输出: OK
```

### 1.3 目录结构

确保以下目录存在:

```bash
# 创建数据目录
mkdir -p data/messages/raw
mkdir -p data/parquet/messages
mkdir -p data/metadata/checkpoints
mkdir -p data/archive/messages
```

---

## 2. 基本用法

### 2.1 追加消息到 JSONL

```python
from diting.services.storage.jsonl_writer import JSONLWriter

# 初始化写入器
writer = JSONLWriter(base_dir="data/messages/raw")

# 追加单条消息
message = {
    "msg_id": "1234567890",
    "from_username": "wxid_abc123",
    "to_username": "filehelper",
    "content": "Hello World",
    "create_time": 1737590400,
    "msg_type": 1,
    "is_chatroom_msg": 0,
    "chatroom": "",
    "chatroom_sender": "",
    "desc": "",
    "source": "0",
    "guid": "550e8400-e29b-41d4-a716-446655440000",
    "notify_type": 100
}

writer.append_message(message)
print("消息已追加到当日 JSONL 文件")
```

### 2.2 转换 JSONL 到 Parquet

```python
from diting.services.storage.jsonl_to_parquet import JSONLToParquetConverter
from pathlib import Path

# 初始化转换器
converter = JSONLToParquetConverter(batch_size=10_000)

# 转换单个文件
stats = converter.convert_to_parquet(
    jsonl_path=Path("data/messages/raw/2026-01-23.jsonl"),
    parquet_path=Path("data/parquet/messages/year=2026/month=01/day=23/data.parquet")
)

print(f"转换完成:")
print(f"  记录数: {stats['total_records']}")
print(f"  压缩率: {stats['compression_ratio']:.2f}x")
print(f"  原始大小: {stats['source_size_mb']:.2f} MB")
print(f"  压缩后: {stats['target_size_mb']:.2f} MB")
```

### 2.3 查询消息

```python
from diting.services.storage.query import query_messages

# 查询最近 3 天的所有消息
df = query_messages(
    start_date="2026-01-20",
    end_date="2026-01-23",
    parquet_root="data/parquet/messages"
)

print(f"查询到 {len(df)} 条消息")
print(df.head())

# 查询特定群聊的消息
df_chatroom = query_messages(
    start_date="2026-01-20",
    end_date="2026-01-23",
    filters={"chatroom": "chatroom_123"},
    columns=["msg_id", "from_username", "content", "create_time"]
)

print(f"群聊消息: {len(df_chatroom)} 条")
```

---

## 3. CLI 命令用法

### 3.1 每日摄入任务

```bash
# 摄入今天的 JSONL 文件到 Parquet
uv run python -m diting.cli.storage dump-parquet

# 摄入指定日期
uv run python -m diting.cli.storage dump-parquet --date 2026-01-23

# 跳过已存在的 Parquet 文件(默认)
uv run python -m diting.cli.storage dump-parquet --skip-existing

# 强制覆盖
uv run python -m diting.cli.storage dump-parquet --overwrite
```

### 3.2 查询命令

```bash
# 查询最近 7 天的消息
uv run python -m diting.cli.storage query \
    --start 2026-01-16 \
    --end 2026-01-23

# 按群聊过滤
uv run python -m diting.cli.storage query \
    --start 2026-01-20 \
    --end 2026-01-23 \
    --chatroom chatroom_123

# 导出为 CSV
uv run python -m diting.cli.storage query \
    --start 2026-01-20 \
    --end 2026-01-23 \
    --output messages.csv
```

### 3.3 验证命令

```bash
# 验证特定分区
uv run python -m diting.cli.storage validate \
    --partition "data/parquet/messages/year=2026/month=01/day=23"

# 验证所有分区
uv run python -m diting.cli.storage validate --all

# 检测重复消息
uv run python -m diting.cli.storage detect-duplicates
```

### 3.4 清理命令

```bash
# 清理 7 天前的 JSONL 文件(试运行)
uv run python -m diting.cli.storage cleanup \
    --retention-days 7 \
    --dry-run

# 实际执行清理
uv run python -m diting.cli.storage cleanup \
    --retention-days 7
```

---

## 4. 自动化任务配置

### 4.1 配置 Systemd Timer

#### 安装服务文件

```bash
# 复制服务文件
sudo cp deploy/diting-parquet-dump.service /etc/systemd/system/
sudo cp deploy/diting-parquet-dump.timer /etc/systemd/system/

# 重新加载 systemd
sudo systemctl daemon-reload

# 启用 Timer
sudo systemctl enable diting-parquet-dump.timer

# 启动 Timer
sudo systemctl start diting-parquet-dump.timer
```

#### 验证 Timer

```bash
# 查看 Timer 状态
sudo systemctl status diting-parquet-dump.timer

# 查看下次执行时间
sudo systemctl list-timers diting-parquet-dump.timer

# 手动触发(测试)
sudo systemctl start diting-parquet-dump.service

# 查看日志
sudo journalctl -u diting-parquet-dump.service -f
```

#### 修改执行时间

编辑 `/etc/systemd/system/diting-parquet-dump.timer`:

```ini
[Timer]
# 修改为每天凌晨 03:00 执行
OnCalendar=*-*-* 03:00:00

# 保存后重新加载
sudo systemctl daemon-reload
sudo systemctl restart diting-parquet-dump.timer
```

---

## 5. 常见场景

### 5.1 批量导入历史数据

```python
from diting.services.storage.batch_converter import BatchConverter
from diting.services.storage.jsonl_to_parquet import JSONLToParquetConverter
from pathlib import Path

# 初始化批量转换器
converter = JSONLToParquetConverter(batch_size=10_000)
batch_converter = BatchConverter(
    raw_dir=Path("data/messages/raw"),
    parquet_dir=Path("data/parquet/messages"),
    converter=converter
)

# 转换所有 JSONL 文件
stats = batch_converter.convert_all(skip_existing=True)

print(f"批量转换完成:")
print(f"  转换文件: {stats['converted']}")
print(f"  跳过文件: {stats['skipped']}")
print(f"  失败文件: {stats['failed']}")
```

### 5.2 增量处理新消息

```python
from diting.services.storage.incremental import incremental_ingest

# 增量摄入(自动从检查点继续)
result = incremental_ingest(
    source_jsonl="data/messages/raw/2026-01-23.jsonl",
    parquet_root="data/parquet/messages",
    checkpoint_dir="data/metadata/checkpoints"
)

print(f"增量处理完成:")
print(f"  新增记录: {result['new_records']}")
print(f"  去重后: {result['deduplicated']}")
print(f"  跳过重复: {result['skipped_duplicates']}")
```

### 5.3 归档冷数据

```python
from diting.services.storage.archive import archive_old_partitions

# 归档 90 天前的数据
result = archive_old_partitions(
    parquet_root="data/parquet/messages",
    archive_root="data/archive/messages",
    older_than_days=90,
    compression="zstd",
    compression_level=19
)

print(f"归档完成:")
print(f"  归档分区: {result['archived_partitions']}")
print(f"  原始大小: {result['total_size_before_mb']:.2f} MB")
print(f"  压缩后: {result['total_size_after_mb']:.2f} MB")
print(f"  压缩率: {result['compression_ratio']:.2f}x")
```

### 5.4 按条件过滤查询

```python
from diting.services.storage.query import query_messages

# 查询特定用户的消息
df = query_messages(
    start_date="2026-01-01",
    end_date="2026-01-31",
    filters={
        "from_username": "wxid_abc123",
        "msg_type": 1  # 文本消息
    },
    columns=["msg_id", "content", "create_time"]
)

# 按时间排序
df = df.sort_values("create_time")

# 导出为 CSV
df.to_csv("user_messages.csv", index=False)
print(f"已导出 {len(df)} 条消息到 user_messages.csv")
```

### 5.5 验证数据完整性

```python
from diting.services.storage.validation import validate_partition, detect_duplicates

# 验证特定分区
result = validate_partition("data/parquet/messages/year=2026/month=01/day=23")

if result["is_valid"]:
    print(f"✓ 分区有效:")
    print(f"  文件数: {result['file_count']}")
    print(f"  记录数: {result['total_records']}")
    print(f"  总大小: {result['total_size_bytes'] / 1024 / 1024:.2f} MB")
else:
    print("✗ 分区无效:")
    for error in result["errors"]:
        print(f"  - {error}")

# 检测重复消息
duplicates = detect_duplicates("data/parquet/messages")

if len(duplicates) > 0:
    print(f"⚠ 发现 {len(duplicates)} 个重复消息:")
    print(duplicates)
else:
    print("✓ 无重复消息")
```

---

## 6. 监控与调试

### 6.1 查看日志

```bash
# 查看 Systemd 服务日志
sudo journalctl -u diting-parquet-dump.service -n 100

# 实时查看日志
sudo journalctl -u diting-parquet-dump.service -f

# 查看特定日期的日志
sudo journalctl -u diting-parquet-dump.service --since "2026-01-23 02:00:00"

# 过滤错误日志
sudo journalctl -u diting-parquet-dump.service -p err
```

### 6.2 性能分析

```python
import time
from diting.services.storage.query import query_messages

# 测量查询性能
start = time.time()
df = query_messages(
    start_date="2026-01-01",
    end_date="2026-01-31"
)
elapsed = time.time() - start

print(f"查询 {len(df)} 条记录耗时: {elapsed:.2f} 秒")

# 预期: 单日查询 <1 秒, 月度查询 <5 秒
```

### 6.3 磁盘空间监控

```bash
# 查看数据目录大小
du -sh data/messages/raw
du -sh data/parquet/messages
du -sh data/archive/messages

# 查看分区详细大小
du -h data/parquet/messages/year=2026/month=01/ | sort -h

# 监控磁盘使用率
df -h /opt/diting/data
```

---

## 7. 故障排查

### 7.1 文件锁超时

**问题**: `OSError: Failed to acquire file lock`

**原因**: 多个进程同时写入 JSONL 文件

**解决**:
1. 检查是否有多个定时任务同时运行
2. 增加锁超时时间(默认 5 秒)
3. 确保 Systemd Timer 配置正确

```python
# 增加超时时间
writer = JSONLWriter(base_dir="data/messages/raw", lock_timeout=10)
```

---

### 7.2 Parquet 文件损坏

**问题**: `pyarrow.lib.ArrowInvalid: Parquet file size is 0 bytes`

**原因**: 写入过程中进程崩溃

**解决**:
1. 删除损坏的 Parquet 文件
2. 重新运行转换命令

```bash
# 查找 0 字节文件
find data/parquet -name "*.parquet" -size 0

# 删除损坏文件
find data/parquet -name "*.parquet" -size 0 -delete

# 重新转换
uv run python -m diting.cli.storage dump-parquet --date 2026-01-23
```

---

### 7.3 内存不足

**问题**: `MemoryError` 或进程被 OOM Killer 终止

**原因**: 批量大小过大或数据量超出预期

**解决**:
1. 减小批量大小(默认 10,000 → 5,000)
2. 增加系统内存限制

```python
# 减小批量大小
converter = JSONLToParquetConverter(batch_size=5_000)
```

或修改 Systemd 服务:

```ini
# /etc/systemd/system/diting-parquet-dump.service
[Service]
MemoryMax=4G  # 增加到 4GB
```

---

### 7.4 Schema 不兼容

**问题**: `pyarrow.lib.ArrowInvalid: Schema mismatch`

**原因**: 微信 API 返回数据结构变化

**解决**:
1. 查看错误日志确定不兼容字段
2. 更新 Schema 定义
3. 使用 `extra_fields` 字段保存未知字段

```python
# 临时解决: 跳过 Schema 验证
converter.convert_to_parquet(
    jsonl_path=jsonl_path,
    parquet_path=parquet_path,
    schema=None  # 自动推断 Schema
)
```

---

## 8. 最佳实践

### 8.1 数据备份

定期备份关键数据:

```bash
# 备份 JSONL 文件(最近 7 天)
rsync -av --relative data/messages/raw ./backup/

# 备份 Parquet 文件(最近 30 天)
find data/parquet -mtime -30 -type f | rsync -av --files-from=- . ./backup/

# 备份检查点
rsync -av data/metadata/checkpoints ./backup/
```

### 8.2 定期维护

每月执行维护任务:

```bash
# 1. 验证所有分区
uv run python -m diting.cli.storage validate --all

# 2. 检测重复消息
uv run python -m diting.cli.storage detect-duplicates

# 3. 归档冷数据
uv run python -m diting.cli.storage archive --older-than-days 90

# 4. 清理过期 JSONL
uv run python -m diting.cli.storage cleanup --retention-days 7
```

### 8.3 性能优化

- **查询优化**: 尽量使用日期范围过滤,避免全表扫描
- **列裁剪**: 只查询需要的列,减少 I/O
- **批量处理**: 合并多个小查询为单个大查询
- **分区合并**: 定期合并 <10MB 的小分区文件

---

## 9. 下一步

- 📖 阅读 [data-model.md](./data-model.md) 了解数据模型详情
- 📖 阅读 [contracts/storage-api.md](./contracts/storage-api.md) 了解完整 API
- 🔨 查看 [tasks.md](./tasks.md) 了解实现任务清单
- 🧪 运行测试: `uv run pytest tests/unit/test_storage.py -v`

---

## 10. 获取帮助

- **CLI 帮助**: `uv run python -m diting.cli.storage --help`
- **API 文档**: 查看 `contracts/storage-api.md`
- **问题反馈**: 在 GitHub Issues 提交问题
- **代码示例**: 查看 `tests/integration/test_storage_pipeline.py`
