"""Schema 版本管理

提供 schema 版本注册、查询和兼容性检查功能。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa


class SchemaRegistry:
    """Schema 版本注册表

    管理 Parquet schema 的版本历史，支持 schema 演化和兼容性检查。
    """

    def __init__(self, registry_path: str | Path):
        """初始化 Schema Registry

        Args:
            registry_path: 注册表文件路径（JSON 格式）
        """
        self.registry_path = Path(registry_path)
        self.schemas: dict[str, list[dict[str, Any]]] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """从文件加载注册表"""
        if self.registry_path.exists():
            with open(self.registry_path, encoding="utf-8") as f:
                self.schemas = json.load(f)
        else:
            # 创建空注册表
            self.schemas = {}
            self._save_registry()

    def _save_registry(self) -> None:
        """保存注册表到文件"""
        # 确保目录存在
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self.schemas, f, indent=2, ensure_ascii=False)

    def register_schema(self, schema_name: str, schema: pa.Schema, description: str = "") -> int:
        """注册新的 schema 版本

        Args:
            schema_name: Schema 名称（如 "message_content", "contact_sync"）
            schema: PyArrow Schema 对象
            description: 版本描述

        Returns:
            新注册的版本号
        """
        # 序列化 schema 为 JSON
        schema_dict = {
            "fields": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in schema
            ]
        }

        # 获取当前版本号
        if schema_name not in self.schemas:
            self.schemas[schema_name] = []

        version = len(self.schemas[schema_name]) + 1

        # 添加新版本
        version_entry = {
            "version": version,
            "schema": schema_dict,
            "description": description,
            "registered_at": datetime.now().isoformat(),
        }

        self.schemas[schema_name].append(version_entry)
        self._save_registry()

        return version

    def get_schema(self, schema_name: str, version: int | None = None) -> pa.Schema | None:
        """获取指定版本的 schema

        Args:
            schema_name: Schema 名称
            version: 版本号（None 表示最新版本）

        Returns:
            PyArrow Schema 对象，如果不存在则返回 None
        """
        if schema_name not in self.schemas:
            return None

        versions = self.schemas[schema_name]
        if not versions:
            return None

        # 获取指定版本或最新版本
        if version is None:
            version_entry = versions[-1]
        else:
            matching_versions = [v for v in versions if v["version"] == version]
            if not matching_versions:
                return None
            version_entry = matching_versions[0]

        # 反序列化 schema
        fields = []
        for field_dict in version_entry["schema"]["fields"]:
            # 简单的类型映射（可以扩展）
            type_str = field_dict["type"]
            if type_str == "string":
                field_type = pa.string()
            elif type_str == "int64":
                field_type = pa.int64()
            elif type_str == "int32":
                field_type = pa.int32()
            elif type_str == "bool":
                field_type = pa.bool_()
            elif type_str == "double":
                field_type = pa.float64()
            else:
                # 尝试解析复杂类型
                field_type = pa.string()  # 默认为 string

            fields.append(pa.field(field_dict["name"], field_type, field_dict["nullable"]))

        return pa.schema(fields)

    def get_latest_version(self, schema_name: str) -> int | None:
        """获取最新版本号

        Args:
            schema_name: Schema 名称

        Returns:
            最新版本号，如果不存在则返回 None
        """
        if schema_name not in self.schemas or not self.schemas[schema_name]:
            return None

        version: int = self.schemas[schema_name][-1]["version"]
        return version

    def list_versions(self, schema_name: str) -> list[dict[str, Any]]:
        """列出所有版本

        Args:
            schema_name: Schema 名称

        Returns:
            版本列表，每个版本包含 version, description, registered_at
        """
        if schema_name not in self.schemas:
            return []

        return [
            {
                "version": v["version"],
                "description": v["description"],
                "registered_at": v["registered_at"],
            }
            for v in self.schemas[schema_name]
        ]

    def is_compatible(
        self, schema_name: str, new_schema: pa.Schema, base_version: int | None = None
    ) -> dict[str, Any]:
        """检查新 schema 是否与基础版本兼容

        兼容性规则：
        - 可以添加新字段（向后兼容）
        - 不能删除现有字段（破坏性变更）
        - 不能更改字段类型（破坏性变更）

        Args:
            schema_name: Schema 名称
            new_schema: 新的 PyArrow Schema
            base_version: 基础版本号（None 表示最新版本）

        Returns:
            兼容性检查结果，包含:
            - is_compatible: 是否兼容
            - added_fields: 新增的字段列表
            - removed_fields: 删除的字段列表
            - changed_fields: 类型变更的字段列表
            - errors: 错误列表
        """
        base_schema = self.get_schema(schema_name, base_version)

        if base_schema is None:
            # 如果没有基础版本，认为是兼容的（首次注册）
            return {
                "is_compatible": True,
                "added_fields": [field.name for field in new_schema],
                "removed_fields": [],
                "changed_fields": [],
                "errors": [],
            }

        # 获取字段名集合
        base_field_names = {field.name for field in base_schema}
        new_field_names = {field.name for field in new_schema}

        # 检查新增字段
        added_fields = list(new_field_names - base_field_names)

        # 检查删除字段（破坏性变更）
        removed_fields = list(base_field_names - new_field_names)

        # 检查类型变更（破坏性变更）
        changed_fields = []
        for field_name in base_field_names & new_field_names:
            base_field = base_schema.field(field_name)
            new_field = new_schema.field(field_name)

            if not base_field.type.equals(new_field.type):
                changed_fields.append(
                    {
                        "field": field_name,
                        "old_type": str(base_field.type),
                        "new_type": str(new_field.type),
                    }
                )

        # 生成错误列表
        errors = []
        if removed_fields:
            errors.append(f"删除字段（破坏性变更）: {', '.join(removed_fields)}")
        if changed_fields:
            for change in changed_fields:
                errors.append(
                    f"字段 '{change['field']}' 类型变更（破坏性变更）: "
                    f"{change['old_type']} -> {change['new_type']}"
                )

        # 判断是否兼容
        is_compatible = len(errors) == 0

        return {
            "is_compatible": is_compatible,
            "added_fields": added_fields,
            "removed_fields": removed_fields,
            "changed_fields": changed_fields,
            "errors": errors,
        }
