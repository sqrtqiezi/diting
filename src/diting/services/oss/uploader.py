from __future__ import annotations

import datetime as dt
import secrets
from pathlib import Path

import oss2

from diting.endpoints.wechat.config import OSSConfig


class OSSUploader:
    def __init__(self, config: OSSConfig):
        self.config = config
        auth = oss2.Auth(config.access_key_id, config.access_key_secret)
        self.bucket = oss2.Bucket(auth, config.endpoint, config.bucket)

        if config.public_base_url:
            self.public_base_url = config.public_base_url.rstrip("/")
        else:
            endpoint = config.endpoint
            if endpoint.startswith("http://") or endpoint.startswith("https://"):
                endpoint = endpoint.split("://", 1)[1]
            self.public_base_url = f"https://{config.bucket}.{endpoint}".rstrip("/")

    def upload_file_public(self, local_path: Path) -> tuple[str, str]:
        """上传文件并返回 (object_key, public_url)。"""
        if not local_path.exists() or not local_path.is_file():
            raise FileNotFoundError(f"文件不存在: {local_path}")

        date_part = dt.datetime.now(dt.UTC).strftime("%Y%m%d")
        token = secrets.token_hex(8)
        object_key = f"{self.config.prefix.strip('/')}/{date_part}/{token}_{local_path.name}"

        with local_path.open("rb") as f:
            self.bucket.put_object(object_key, f)

        # 确保对象可公开访问（public-read）
        self.bucket.put_object_acl(object_key, oss2.OBJECT_ACL_PUBLIC_READ)

        public_url = f"{self.public_base_url}/{object_key}"
        return object_key, public_url

