# 数据模型设计：微信消息数据湖存储

**功能分支**: `006-wechat-message-storage`
**设计日期**: 2026-01-23
**相关文档**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md)

## 概述

本文档定义微信消息数据湖存储的核心数据实体、字段定义、关系模型和验证规则。

---

## 核心实体

### 1. MessageContent (消息内容记录)

表示微信消息的核心数据(占总消息的 98%)。

#### 字段定义

| 字段名 | 类型 | 必填 | 默认值 | 描述 | 验证规则 |
|--------|------|------|--------|------|---------|
| `msg_id` | string | ✅ | - | 微信消息唯一 ID | 非空,用于去重 |
| `from_username` | string | ✅ | - | 发送端账号 | 非空 |
| `to_username` | string | ✅ | - | 接收端账号 | 非空 |
| `chatroom` | string | ❌ | `""` | 群聊 ID,私聊时为空 | - |
| `chatroom_sender` | string | ❌ | `""` | 群聊发言者,非群聊时为空 | - |
| `msg_type` | int32 | ✅ | - | 消息类型代码 | ≥0 |
| `create_time` | int64 | ✅ | - | Unix 时间戳(秒) | >0, <2^31-1 |
| `is_chatroom_msg` | int8 | ✅ | - | 是否群消息(1=群,0=私聊) | 0 或 1 |
| `content` | string | ❌ | `""` | 消息主体内容(通常为 XML) | - |
| `desc` | string | ❌ | `""` | 外层描述 | - |
| `source` | string | ✅ | - | 消息来源(XML 字符串或整数) | 统一为字符串存储 |
| `guid` | string | ✅ | - | Webhook 事件唯一 ID | 非空 |
| `notify_type` | int32 | ✅ | - | 通知类型 ID | ≥0 |
| `ingestion_time` | timestamp | ✅ | 当前时间 | 数据摄入时间戳(UTC) | 自动生成 |

#### 分区字段

| 字段名 | 类型 | 描述 | 来源 |
|--------|------|------|------|
| `year` | int16 | 年份(YYYY) | 从 `create_time` 提取 |
| `month` | int8 | 月份(MM, 1-12) | 从 `create_time` 提取 |
| `day` | int8 | 日期(DD, 1-31) | 从 `create_time` 提取 |

#### 关系

- **属于**: Chatroom (通过 `chatroom` 字段)
- **发送者**: User (通过 `from_username` 字段)
- **接收者**: User (通过 `to_username` 字段)
- **消息类型**: MessageType (通过 `msg_type` 字段)

#### 索引策略

- **主键**: `msg_id` (用于去重)
- **分区键**: `(year, month, day)` (用于时间范围查询)
- **查询优化字段**: `chatroom`, `from_username`, `msg_type` (字典编码)

#### 状态转换

消息状态为不可变,一旦写入不允许修改(仅追加模式)。

---

### 2. ContactSync (联系人同步记录)

表示微信联系人/聊天室同步数据(占总消息的 1.6%)。

#### 字段定义

| 字段名 | 类型 | 必填 | 默认值 | 描述 | 验证规则 |
|--------|------|------|--------|------|---------|
| `username` | string | ✅ | - | 用户名(唯一标识) | 非空 |
| `alias` | string | ❌ | `""` | 用户别名 | - |
| `encryptUserName` | string | ❌ | `""` | 加密用户名 | - |
| `contactType` | int32 | ❌ | 0 | 联系人类型 | ≥0 |
| `deleteFlag` | int8 | ❌ | 0 | 删除标记(0=正常,1=已删除) | 0 或 1 |
| `verifyFlag` | int32 | ❌ | 0 | 验证标记 | ≥0 |
| `sex` | int8 | ❌ | 0 | 性别(0=未知,1=男,2=女) | 0-2 |
| `country` | string | ❌ | `""` | 国家 | - |
| `province` | string | ❌ | `""` | 省份 | - |
| `city` | string | ❌ | `""` | 城市 | - |
| `mobile` | string | ❌ | `""` | 手机号(敏感) | 可选脱敏 |
| `nickName` | string | ❌ | `"{}"` | 昵称(JSON 字符串) | 有效 JSON |
| `remark` | string | ❌ | `"{}"` | 备注(JSON 字符串) | 有效 JSON |
| `snsUserInfo` | string | ❌ | `"{}"` | 社交信息(JSON 字符串) | 有效 JSON |
| `customInfo` | string | ❌ | `"{}"` | 企业扩展信息(JSON 字符串) | 有效 JSON |
| `guid` | string | ✅ | - | Webhook 事件唯一 ID | 非空 |
| `notify_type` | int32 | ✅ | - | 通知类型 ID | ≥0 |
| `ingestion_time` | timestamp | ✅ | 当前时间 | 数据摄入时间戳(UTC) | 自动生成 |

#### 分区字段

同 MessageContent,基于 `ingestion_time` 提取年/月/日。

#### 关系

- **表示**: Contact (联系人实体)
- **表示**: Chatroom (聊天室实体,当 `contactType` 表明为群聊)

#### 索引策略

- **主键**: `username` (用于去重)
- **分区键**: `(year, month, day)` (基于 `ingestion_time`)

---

### 3. StoragePartition (存储分区元数据)

表示 Parquet 文件分区的元数据信息。

#### 字段定义

| 字段名 | 类型 | 必填 | 默认值 | 描述 |
|--------|------|------|--------|------|
| `partition_key` | string | ✅ | - | 分区键(格式: `YYYY-MM-DD`) |
| `record_count` | int64 | ✅ | 0 | 分区内记录数 |
| `file_path` | string | ✅ | - | Parquet 文件绝对路径 |
| `size_bytes` | int64 | ✅ | 0 | 文件大小(字节) |
| `created_at` | timestamp | ✅ | - | 分区创建时间 |
| `last_updated_at` | timestamp | ✅ | - | 最后更新时间 |
| `compression` | string | ✅ | `"snappy"` | 压缩算法 |
| `schema_version` | int32 | ✅ | 1 | Schema 版本号 |

#### 关系

- **包含**: MessageContent / ContactSync (一对多)

---

### 4. ProcessingCheckpoint (处理检查点)

跟踪增量处理进度,支持断点续传。

#### 字段定义

| 字段名 | 类型 | 必填 | 默认值 | 描述 |
|--------|------|------|--------|------|
| `source_file` | string | ✅ | - | 源 JSONL 文件路径 |
| `last_processed_line` | int64 | ✅ | 0 | 最后处理的行号 |
| `last_processed_msg_id` | string | ❌ | `""` | 最后处理的消息 ID |
| `last_processed_timestamp` | int64 | ❌ | 0 | 最后处理的消息时间戳 |
| `processed_record_count` | int64 | ✅ | 0 | 已处理记录总数 |
| `checkpoint_time` | timestamp | ✅ | - | 检查点创建时间 |
| `status` | string | ✅ | `"processing"` | 状态(processing/completed/failed) |
| `error_message` | string | ❌ | `""` | 错误信息(如有) |

#### 状态转换

```text
processing → completed (成功完成)
processing → failed (发生错误)
failed → processing (重试)
```

#### 关系

- **引用**: Source JSONL File (通过 `source_file`)

---

## 数据流转模型

### 1. 摄入流程 (Ingestion Flow)

```text
Webhook 日志 (JSONL)
    ↓ [每日凌晨 02:00]
读取检查点 (ProcessingCheckpoint)
    ↓
增量读取新消息
    ↓
字段类型归一化 (source: int→str)
    ↓
添加分区字段 (year/month/day)
    ↓
去重 (基于 msg_id)
    ↓
区分消息类型 (MessageContent / ContactSync)
    ↓
原子写入 Parquet 分区
    ↓
更新检查点
    ↓
记录分区元数据 (StoragePartition)
```

### 2. 查询流程 (Query Flow)

```text
用户查询请求 (日期范围 + 过滤条件)
    ↓
查询分区元数据 (确定相关分区)
    ↓
分区裁剪 (Partition Pruning)
    ↓
读取相关 Parquet 文件 (仅需要的列)
    ↓
谓词下推过滤 (Predicate Pushdown)
    ↓
合并结果
    ↓
返回 DataFrame / 记录列表
```

---

## 数据验证规则

### 1. 消息内容验证 (MessageContent)

| 规则 | 描述 | 错误处理 |
|------|------|---------|
| `msg_id` 唯一性 | 同一 `msg_id` 不允许重复 | 跳过重复消息,记录警告 |
| `create_time` 范围 | 时间戳必须在合理范围内 | 记录错误,跳过该消息 |
| `source` 类型转换 | 统一转换为字符串 | 自动转换,int→str |
| 必填字段检查 | `msg_id`, `from_username` 等不能为空 | 记录错误,跳过该消息 |

### 2. 联系人同步验证 (ContactSync)

| 规则 | 描述 | 错误处理 |
|------|------|---------|
| `username` 唯一性 | 同一 `username` 只保留最新记录 | 覆盖旧记录 |
| JSON 字段有效性 | `nickName`, `remark` 等必须是有效 JSON | 解析失败时存储空对象 `"{}"` |
| `mobile` 脱敏 | 可选的敏感信息脱敏 | 隐藏中间 4 位(如启用) |

### 3. 分区验证

| 规则 | 描述 | 错误处理 |
|------|------|---------|
| 分区完整性 | 分区目录必须包含有效 Parquet 文件 | 标记为损坏分区 |
| 文件大小检查 | Parquet 文件不能为 0 字节 | 删除并重新生成 |
| Schema 一致性 | 同分区内 Schema 必须一致 | 使用最新 Schema 重写 |

---

## Parquet Schema 定义

### 1. MessageContent Schema

```python
import pyarrow as pa

MESSAGE_CONTENT_SCHEMA = pa.schema([
    # 核心字段
    ('msg_id', pa.string()),
    ('from_username', pa.string()),
    ('to_username', pa.string()),
    ('chatroom', pa.string()),
    ('chatroom_sender', pa.string()),
    ('msg_type', pa.int32()),
    ('create_time', pa.timestamp('s', tz='UTC')),  # Unix 时间戳→datetime
    ('is_chatroom_msg', pa.int8()),
    ('content', pa.string()),
    ('desc', pa.string()),
    ('source', pa.string()),  # 统一为字符串

    # 元数据字段
    ('guid', pa.string()),
    ('notify_type', pa.int32()),
    ('ingestion_time', pa.timestamp('s', tz='UTC')),

    # 分区字段(物理分区,不存储在列中)
    # ('year', pa.int16()),
    # ('month', pa.int8()),
    # ('day', pa.int8()),
])
```

### 2. ContactSync Schema

```python
CONTACT_SYNC_SCHEMA = pa.schema([
    # 基本信息
    ('username', pa.string()),
    ('alias', pa.string()),
    ('encryptUserName', pa.string()),

    # 状态标志
    ('contactType', pa.int32()),
    ('deleteFlag', pa.int8()),
    ('verifyFlag', pa.int32()),
    ('sex', pa.int8()),

    # 地理信息
    ('country', pa.string()),
    ('province', pa.string()),
    ('city', pa.string()),
    ('mobile', pa.string()),

    # 嵌套结构(序列化为 JSON 字符串)
    ('nickName', pa.string()),
    ('remark', pa.string()),
    ('snsUserInfo', pa.string()),
    ('customInfo', pa.string()),

    # 元数据
    ('guid', pa.string()),
    ('notify_type', pa.int32()),
    ('ingestion_time', pa.timestamp('s', tz='UTC')),
])
```

### 3. Schema 演化策略

| 变更类型 | 处理方式 | 示例 |
|---------|---------|------|
| **新增字段** | 写入新 Schema,旧文件读取时填充 NULL | 微信新增 `reaction` 字段 |
| **删除字段** | 查询时不读取该列 | 移除废弃的 `desc` 字段 |
| **类型变更** | 应用层统一类型,Parquet 保持不变 | `source` 统一为字符串 |
| **重命名字段** | 维护列名映射表 | `from_username` → `sender` |

---

## 数据字典编码优化

### 高基数字段(字典编码)

以下字段启用 Parquet 字典编码以提升压缩率:

| 字段 | 唯一值估计 | 压缩提升 |
|------|-----------|---------|
| `from_username` | ~500 | 5-10x |
| `to_username` | ~10 | 10-20x |
| `chatroom` | ~50 | 10-15x |
| `chatroom_sender` | ~500 | 5-10x |
| `msg_type` | ~20 | 50-100x |

### 低基数字段(不使用字典编码)

| 字段 | 原因 |
|------|------|
| `content` | 高唯一性,字典编码无效 |
| `source` | 多为 XML,唯一性高 |
| `msg_id` | 完全唯一,不适合字典编码 |

---

## 数据保留与归档策略

### 1. 热数据 (0-7 天)

- **存储位置**: `data/messages/raw/*.jsonl` (JSONL)
- **访问频率**: 高
- **保留策略**: 转换为 Parquet 后保留 7 天

### 2. 温数据 (7-90 天)

- **存储位置**: `data/parquet/messages/` (Parquet + Snappy)
- **访问频率**: 中
- **保留策略**: 永久保留

### 3. 冷数据 (>90 天)

- **存储位置**: `data/archive/messages/` (Parquet + Zstd-19)
- **访问频率**: 低
- **保留策略**: 按需归档,压缩率可达 70-80%

---

## 示例数据

### MessageContent 示例

```json
{
  "msg_id": "1234567890",
  "from_username": "wxid_abc123",
  "to_username": "filehelper",
  "chatroom": "",
  "chatroom_sender": "",
  "msg_type": 1,
  "create_time": 1737590400,
  "is_chatroom_msg": 0,
  "content": "Hello World",
  "desc": "",
  "source": "0",
  "guid": "550e8400-e29b-41d4-a716-446655440000",
  "notify_type": 100,
  "ingestion_time": "2026-01-23T02:05:30Z",
  "year": 2026,
  "month": 1,
  "day": 23
}
```

### ContactSync 示例

```json
{
  "username": "wxid_abc123",
  "alias": "Alice",
  "encryptUserName": "v1_abc...",
  "contactType": 1,
  "deleteFlag": 0,
  "verifyFlag": 0,
  "sex": 2,
  "country": "CN",
  "province": "Beijing",
  "city": "Haidian",
  "mobile": "138****1234",
  "nickName": "{\"buffer\": \"QWxpY2U=\"}",
  "remark": "{}",
  "snsUserInfo": "{}",
  "customInfo": "{}",
  "guid": "550e8400-e29b-41d4-a716-446655440001",
  "notify_type": 101,
  "ingestion_time": "2026-01-23T02:05:35Z"
}
```

---

## 性能优化策略

### 1. 查询优化

- **分区裁剪**: 按 `year/month/day` 过滤,仅扫描相关分区
- **列裁剪**: 仅读取需要的列(如查询只需 `msg_id`, `content`)
- **谓词下推**: 在 Parquet 文件级别过滤,减少数据传输
- **字典编码**: 高频字段使用字典编码,减少存储和 I/O

### 2. 写入优化

- **批量写入**: 每批 10,000 条记录
- **原子写入**: Write-Rename 模式,防止部分写入
- **并发控制**: 文件锁 + 单进程写入
- **压缩算法**: Snappy(查询优先) / Zstd-19(归档)

### 3. 存储优化

- **小文件合并**: 定期合并 <10MB 的分区文件
- **冷数据归档**: 90 天后重新压缩为 Zstd-19
- **JSONL 清理**: 7 天后自动删除原始 JSONL 文件

---

## 总结

本数据模型设计确保:
1. ✅ **高性能**: 分区裁剪 + 列存储 + 字典编码
2. ✅ **可扩展性**: Schema 演化支持 + 分区策略
3. ✅ **数据完整性**: 去重 + 验证规则 + 原子写入
4. ✅ **存储效率**: 50-70% 压缩率 + 冷热分层存储
