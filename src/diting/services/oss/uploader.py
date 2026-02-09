from __future__ import annotations

import datetime as dt
import os
import secrets
from pathlib import Path

import oss2

from diting.endpoints.wechat.config import AliyunConfig, OSSConfig


class OSSUploader:
    def __init__(self, config: OSSConfig, *, aliyun: AliyunConfig | None = None):
        self.config = config
        # 优先使用 wechat.yaml 的 aliyun.* 作为统一 AK/SK 来源；
        # 兼容旧的 oss.access_key_* 与环境变量回退。
        ak = (
            (aliyun.access_key_id if aliyun else "").strip()
            or (config.access_key_id or "").strip()
            or os.environ.get("ALIYUN_ACCESS_KEY_ID", "").strip()
        )
        sk = (
            (aliyun.access_key_secret if aliyun else "").strip()
            or (config.access_key_secret or "").strip()
            or os.environ.get("ALIYUN_ACCESS_KEY_SECRET", "").strip()
        )
        if not ak or not sk:
            raise ValueError(
                "未配置阿里云 AccessKey。请在 config/wechat.yaml 配置 "
                "oss.access_key_id/oss.access_key_secret，"
                "或配置 aliyun.access_key_id/aliyun.access_key_secret，"
                "或设置环境变量 ALIYUN_ACCESS_KEY_ID/ALIYUN_ACCESS_KEY_SECRET。"
            )

        auth = oss2.Auth(ak, sk)
        self.bucket = oss2.Bucket(auth, config.endpoint, config.bucket)

        if config.public_base_url:
            self.public_base_url = config.public_base_url.rstrip("/")
        else:
            endpoint = config.endpoint
            if endpoint.startswith("http://") or endpoint.startswith("https://"):
                endpoint = endpoint.split("://", 1)[1]
            self.public_base_url = f"https://{config.bucket}.{endpoint}".rstrip("/")

    def upload_file(self, local_path: Path, *, url_mode: str | None = None) -> tuple[str, str]:
        """上传文件并返回 (object_key, url)。

        - public: 上传后设置 public-read，返回直链 URL
        - signed: 对象保持私有，返回预签名 URL（GET）
        """
        if not local_path.exists() or not local_path.is_file():
            raise FileNotFoundError(f"文件不存在: {local_path}")

        date_part = dt.datetime.now(dt.UTC).strftime("%Y%m%d")
        token = secrets.token_hex(8)
        object_key = f"{self.config.prefix.strip('/')}/{date_part}/{token}_{local_path.name}"

        with local_path.open("rb") as f:
            self.bucket.put_object(object_key, f)

        mode = (url_mode or self.config.url_mode).lower()
        if mode == "public":
            # 确保对象可公开访问（public-read）
            self.bucket.put_object_acl(object_key, oss2.OBJECT_ACL_PUBLIC_READ)
            url = f"{self.public_base_url}/{object_key}"
            return object_key, url

        if mode == "signed":
            url = self.bucket.sign_url("GET", object_key, expires=self.config.signed_url_expires)
            return object_key, url

        raise ValueError(f"不支持的 url_mode: {mode!r}")

    # Backward compatibility
    def upload_file_public(self, local_path: Path) -> tuple[str, str]:
        return self.upload_file(local_path, url_mode="public")
