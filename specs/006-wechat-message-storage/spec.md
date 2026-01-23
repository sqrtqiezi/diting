# Feature Specification: WeChat Message Data Lake Storage

**Feature Branch**: `006-wechat-message-storage`
**Created**: 2026-01-23
**Status**: Draft
**Input**: User description: "Design and implement a data lake storage solution for WeChat messages using JSON + Parquet format, supporting message persistence from webhook logs without requiring a database server"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Persist Messages to Structured Storage (Priority: P1)

As a data analyst, I need to convert raw webhook logs into structured storage files so that I can efficiently query and analyze WeChat message history without loading massive JSON files into memory.

**Why this priority**: This is the foundation for all data analysis. Without structured storage, the current 342MB+ log file is difficult to query and analyze. This enables all downstream use cases.

**Independent Test**: Can be fully tested by running the storage pipeline on existing webhook logs and verifying that Parquet files are created with correct schema and all messages are preserved.

**Acceptance Scenarios**:

1. **Given** webhook logs contain 23,210 messages, **When** storage pipeline runs, **Then** all messages are persisted to Parquet files with no data loss
2. **Given** messages have two types (message content 98%, contact sync 1.6%), **When** storage pipeline processes them, **Then** each type is stored in separate Parquet files with appropriate schemas
3. **Given** a new message arrives in webhook log, **When** incremental storage runs, **Then** only new messages are processed and appended to storage
4. **Given** stored Parquet files exist, **When** querying by date range, **Then** results are returned in under 1 second for typical queries (1 day of data)

---

### User Story 2 - Query Historical Messages Efficiently (Priority: P2)

As a data analyst, I need to query historical messages by various criteria (date, sender, chatroom, message type) so that I can extract insights and build knowledge graphs from conversation history.

**Why this priority**: Once data is stored, the ability to query it efficiently is critical for analysis. This enables the knowledge graph feature (Feature 004) and other analytics use cases.

**Independent Test**: Can be tested by running predefined queries against stored data and measuring query performance and result accuracy.

**Acceptance Scenarios**:

1. **Given** messages are stored in Parquet format, **When** querying messages from a specific date, **Then** results are returned without loading entire dataset into memory
2. **Given** messages from multiple chatrooms, **When** filtering by chatroom ID, **Then** only messages from that chatroom are returned
3. **Given** messages with different types (text, image, article), **When** filtering by msg_type, **Then** only matching messages are returned
4. **Given** large date range query (1 month), **When** query executes, **Then** results are returned in under 5 seconds

---

### User Story 3 - Maintain Data Quality and Integrity (Priority: P2)

As a system administrator, I need the storage system to validate data quality and handle schema evolution so that data remains consistent and usable over time.

**Why this priority**: Data quality issues can corrupt analysis results. Schema evolution support ensures the system can adapt to WeChat API changes without breaking existing data.

**Independent Test**: Can be tested by introducing malformed messages and schema changes, then verifying that the system handles them gracefully.

**Acceptance Scenarios**:

1. **Given** a malformed message in webhook log, **When** storage pipeline processes it, **Then** the error is logged and other messages continue processing
2. **Given** WeChat adds new fields to message schema, **When** storage pipeline encounters new fields, **Then** they are preserved in Parquet files without breaking existing queries
3. **Given** duplicate messages in webhook log, **When** storage pipeline runs, **Then** duplicates are detected and skipped based on msg_id
4. **Given** stored data, **When** validation runs, **Then** data integrity checks confirm all required fields are present and types are correct

---

### User Story 4 - Archive and Manage Storage Growth (Priority: P3)

As a system administrator, I need to manage storage growth through partitioning and archival so that the system remains performant and cost-effective as data volume grows.

**Why this priority**: While not critical for MVP, this ensures long-term sustainability. Without it, query performance will degrade and storage costs will grow unbounded.

**Independent Test**: Can be tested by simulating months of data and verifying that partitioning works correctly and old data can be archived.

**Acceptance Scenarios**:

1. **Given** messages spanning multiple months, **When** storage pipeline runs, **Then** data is partitioned by year/month for efficient querying
2. **Given** data older than retention period, **When** archival process runs, **Then** old data is moved to cold storage or deleted per policy
3. **Given** partitioned data, **When** querying recent data (last 7 days), **Then** only relevant partitions are scanned
4. **Given** storage usage metrics, **When** monitoring dashboard is checked, **Then** current storage size and growth rate are visible

---

### Edge Cases

- What happens when webhook log file is corrupted or contains invalid JSON?
  - System should skip corrupted entries, log errors, and continue processing valid entries
- What happens when Parquet file write fails due to disk space?
  - System should detect the error, log it, and retry with exponential backoff
- What happens when message schema changes significantly (breaking change)?
  - System should detect schema incompatibility and create new versioned Parquet files
- What happens when querying data that spans multiple Parquet files?
  - Query engine should automatically merge results from multiple files
- What happens when two processes try to write to storage simultaneously?
  - File locking or atomic writes should prevent data corruption
- What happens when source field type changes (e.g., `source` field is sometimes int, sometimes string)?
  - Schema should use union types or convert to string to handle both cases

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read messages from webhook log files (`data/wechat_webhook.log`) and parse JSON structure
- **FR-002**: System MUST distinguish between message content type (11 fields) and contact sync type (46-55 fields) based on field count
- **FR-003**: System MUST store message content and contact sync data in separate Parquet files with appropriate schemas
- **FR-004**: System MUST preserve all fields from source data including nested structures (XML strings, dictionaries)
- **FR-005**: System MUST partition Parquet files by date (year/month/day) for efficient querying
- **FR-006**: System MUST support incremental processing to avoid reprocessing entire log file
- **FR-007**: System MUST detect and skip duplicate messages based on `msg_id` field
- **FR-008**: System MUST validate data types and handle type inconsistencies (e.g., `source` field as int or string)
- **FR-009**: System MUST log all processing errors (malformed JSON, schema violations) without stopping pipeline
- **FR-010**: System MUST provide query interface to read Parquet files with filtering by date, sender, chatroom, message type
- **FR-011**: System MUST maintain metadata about stored data (record count, date range, file locations)
- **FR-012**: System MUST support schema evolution by preserving unknown fields in Parquet files
- **FR-013**: System MUST compress Parquet files using Snappy or Zstd compression for storage efficiency
- **FR-014**: System MUST provide CLI commands for storage operations (ingest, query, validate, archive)
- **FR-015**: System MUST handle sensitive data fields (mobile, customInfo.detail) with optional masking capability

### Key Entities

- **Message Content Record**: Represents a WeChat message with 11 core fields
  - Attributes: from_username, to_username, chatroom, chatroom_sender, msg_id, msg_type, create_time, is_chatroom_msg, content (XML), desc, source (XML/int)
  - Relationships: Belongs to a chatroom, sent by a user, has a message type
  - Partitioning: By create_time (year/month/day)

- **Contact Sync Record**: Represents contact/chatroom synchronization data with 46-55 fields
  - Attributes: Basic info (alias, username, encryptUserName), status flags (contactType, deleteFlag, verifyFlag), contact settings, image URLs, geographic data, contact remarks, group info, social data, enterprise extensions
  - Relationships: Represents a contact or chatroom entity
  - Partitioning: By sync timestamp (year/month/day)

- **Storage Partition**: Represents a time-based partition of data
  - Attributes: partition_key (year/month/day), record_count, file_path, size_bytes, created_at, last_updated_at
  - Relationships: Contains multiple message or contact records

- **Processing Checkpoint**: Tracks incremental processing progress
  - Attributes: last_processed_offset, last_processed_timestamp, processed_record_count, checkpoint_time
  - Relationships: References source log file

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Storage pipeline processes 23,210 existing messages in under 5 minutes on standard hardware
- **SC-002**: Query performance returns results for single-day queries in under 1 second
- **SC-003**: Storage efficiency achieves at least 50% compression ratio compared to raw JSON logs
- **SC-004**: Data integrity validation confirms 100% of messages are preserved with no data loss
- **SC-005**: Incremental processing adds new messages to storage within 1 minute of webhook log update
- **SC-006**: System handles schema evolution without requiring manual intervention or data migration
- **SC-007**: Query interface supports filtering by date, sender, chatroom, and message type with correct results
- **SC-008**: Storage system operates without requiring external database server or daemon processes

## Assumptions *(optional)*

- Webhook logs are append-only and messages are not modified after writing
- Message IDs (`msg_id`) are unique and can be used for deduplication
- System has sufficient disk space for storing Parquet files (estimated 50% of raw log size)
- Python environment has access to PyArrow/Pandas libraries for Parquet operations
- File system supports atomic writes or file locking for concurrent access protection
- Data retention policy will be defined later (default: keep all data)
- Query workload is primarily analytical (batch queries) rather than transactional (point lookups)
- Parquet files will be stored locally on the same server as the application

## Out of Scope *(optional)*

- Real-time streaming ingestion (batch processing only for MVP)
- Distributed storage across multiple servers
- SQL query interface (Python API only for MVP)
- Data visualization dashboard
- Automatic backup and disaster recovery
- XML parsing of `content` and `source` fields (stored as raw strings)
- Integration with external data lakes (S3, HDFS, etc.)
- User authentication and access control for queries
- Data encryption at rest (file system encryption is sufficient)

## Dependencies *(optional)*

- **Feature 003 (WeChat Notification Webhook)**: Provides the source webhook logs that need to be stored
- **Python Libraries**: PyArrow (Parquet I/O), Pandas (data manipulation), Pydantic (schema validation)
- **File System**: Requires local file system with sufficient space and write permissions
- **Existing Data**: `data/wechat_webhook.log` and `data/parsed_messages_*.json` files

## References *(optional)*

- `docs/wechat-message-schema.md`: Detailed schema documentation for WeChat webhook messages
- Apache Parquet format specification: https://parquet.apache.org/docs/
- PyArrow documentation: https://arrow.apache.org/docs/python/
- Data lake architecture patterns: https://www.databricks.com/glossary/data-lake
