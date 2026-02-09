from __future__ import annotations

from pathlib import Path

import pytest

from diting.endpoints.wechat.config import OSSConfig
from diting.services.oss.uploader import OSSUploader


class _FakeBucket:
    def __init__(self):
        self.put_calls: list[tuple[str, bytes]] = []
        self.acl_calls: list[str] = []
        self.sign_calls: list[tuple[str, str, int]] = []

    def put_object(self, key: str, fp) -> None:
        self.put_calls.append((key, fp.read()))

    def put_object_acl(self, key: str, acl) -> None:  # noqa: ARG002
        self.acl_calls.append(key)

    def sign_url(self, method: str, key: str, *, expires: int) -> str:
        self.sign_calls.append((method, key, expires))
        return f"https://signed.example.com/{key}?exp={expires}"


def test_upload_file_public_builds_expected_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    # Avoid importing/using real network OSS bucket; replace bucket creation.
    fake_bucket = _FakeBucket()

    import diting.services.oss.uploader as uploader_mod

    monkeypatch.setattr(uploader_mod.oss2, "Auth", lambda _ak, _sk: object())
    monkeypatch.setattr(uploader_mod.oss2, "Bucket", lambda _auth, _ep, _b: fake_bucket)
    monkeypatch.setattr(uploader_mod.secrets, "token_hex", lambda _n: "deadbeef")

    class _FakeDatetime:
        @staticmethod
        def now(_tz):
            class _D:
                def strftime(self, _fmt: str) -> str:
                    return "20990101"

            return _D()

    monkeypatch.setattr(uploader_mod.dt, "datetime", _FakeDatetime)

    p = tmp_path / "a.txt"
    p.write_bytes(b"hello")

    cfg = OSSConfig(
        endpoint="oss-cn-test.aliyuncs.com",
        bucket="my-bucket",
        access_key_id="ak_test",
        access_key_secret="sk_test",
        prefix="pfx",
        public_base_url=None,
    )

    uploader = OSSUploader(cfg)
    key, url = uploader.upload_file_public(p)

    assert key == "pfx/20990101/deadbeef_a.txt"
    assert url == "https://my-bucket.oss-cn-test.aliyuncs.com/pfx/20990101/deadbeef_a.txt"
    assert fake_bucket.put_calls and fake_bucket.put_calls[0][0] == key
    assert fake_bucket.acl_calls == [key]
    assert fake_bucket.sign_calls == []


def test_public_base_url_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    fake_bucket = _FakeBucket()

    import diting.services.oss.uploader as uploader_mod

    monkeypatch.setattr(uploader_mod.oss2, "Auth", lambda _ak, _sk: object())
    monkeypatch.setattr(uploader_mod.oss2, "Bucket", lambda _auth, _ep, _b: fake_bucket)
    monkeypatch.setattr(uploader_mod.secrets, "token_hex", lambda _n: "t")

    class _FakeDatetime:
        @staticmethod
        def now(_tz):
            class _D:
                def strftime(self, _fmt: str) -> str:
                    return "20990102"

            return _D()

    monkeypatch.setattr(uploader_mod.dt, "datetime", _FakeDatetime)

    p = tmp_path / "b.bin"
    p.write_bytes(b"x")

    cfg = OSSConfig(
        endpoint="https://oss-cn-test.aliyuncs.com",
        bucket="my-bucket",
        access_key_id="ak_test",
        access_key_secret="sk_test",
        prefix="p",
        public_base_url="https://cdn.example.com/base/",
    )

    uploader = OSSUploader(cfg)
    key, url = uploader.upload_file_public(p)

    assert key == "p/20990102/t_b.bin"
    assert url == "https://cdn.example.com/base/p/20990102/t_b.bin"
    assert fake_bucket.sign_calls == []


def test_upload_file_signed_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    fake_bucket = _FakeBucket()

    import diting.services.oss.uploader as uploader_mod

    monkeypatch.setattr(uploader_mod.oss2, "Auth", lambda _ak, _sk: object())
    monkeypatch.setattr(uploader_mod.oss2, "Bucket", lambda _auth, _ep, _b: fake_bucket)
    monkeypatch.setattr(uploader_mod.secrets, "token_hex", lambda _n: "beef")

    class _FakeDatetime:
        @staticmethod
        def now(_tz):
            class _D:
                def strftime(self, _fmt: str) -> str:
                    return "20990103"

            return _D()

    monkeypatch.setattr(uploader_mod.dt, "datetime", _FakeDatetime)

    p = tmp_path / "c.pdf"
    p.write_bytes(b"pdf")

    cfg = OSSConfig(
        endpoint="oss-cn-test.aliyuncs.com",
        bucket="my-bucket",
        access_key_id="ak_test",
        access_key_secret="sk_test",
        prefix="p",
        url_mode="signed",
        signed_url_expires=300,
        public_base_url=None,
    )

    uploader = OSSUploader(cfg)
    key, url = uploader.upload_file(p)

    assert key == "p/20990103/beef_c.pdf"
    assert url == "https://signed.example.com/p/20990103/beef_c.pdf?exp=300"
    assert fake_bucket.acl_calls == []  # signed 模式不应设置 public-read
    assert fake_bucket.sign_calls == [("GET", key, 300)]
