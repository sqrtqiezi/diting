from __future__ import annotations

import json
import zlib
from hashlib import md5
from pathlib import Path

import click

from diting.endpoints.wechat.client import WeChatAPIClient
from diting.services.oss.uploader import OSSUploader

from .utils import echo_json, load_wechat_config, resolve_guid


def _file_md5_and_crc32(path: Path, *, chunk_size: int = 1024 * 1024) -> tuple[str, int]:
    h = md5()
    crc = 0
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
            crc = zlib.crc32(chunk, crc)
    return h.hexdigest(), crc & 0xFFFFFFFF


def _parse_upload_response(resp: object) -> dict:
    # resp 可能是 dict / str / None
    if resp is None:
        raise ValueError("cloud/upload 返回为空")

    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except Exception as e:
            raise ValueError(f"cloud/upload 返回非 JSON 字符串: {resp!r}") from e

    if not isinstance(resp, dict):
        raise ValueError(f"cloud/upload 返回非对象: {type(resp).__name__}")

    # 常见结构: {errcode:0,data:{...}} 或直接 {...}
    payload = resp.get("data") if isinstance(resp.get("data"), dict) else resp

    file_id = payload.get("file_id") or payload.get("fileId")
    aes_key = payload.get("aes_key") or payload.get("aesKey")
    file_key = payload.get("file_key") or payload.get("fileKey") or ""

    if not file_id or not aes_key:
        raise ValueError(f"cloud/upload 缺少 file_id/aes_key: {payload}")

    return {"file_id": file_id, "aes_key": aes_key, "file_key": file_key}


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("config/wechat.yaml"),
    show_default=True,
    help="微信配置文件路径",
)
@click.option(
    "--device-index",
    "-d",
    type=int,
    default=0,
    show_default=True,
    help="设备索引 (默认: 0 - 第一个设备)",
)
@click.option(
    "--guid",
    "-g",
    default=None,
    help="设备 GUID（可选，优先级高于 --device-index）",
)
@click.option(
    "--to-username",
    required=True,
    help="接收方 username（好友或群）",
)
@click.option(
    "--file",
    "file_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="本地文件路径",
)
@click.option(
    "--file-type",
    type=int,
    default=5,
    show_default=True,
    help="上传类型: 小程序封面图=>1, 图片=>2, 视频=>4, 文件&GIF=>5",
)
@click.option(
    "--oss-url-mode",
    type=click.Choice(["public", "signed"], case_sensitive=False),
    default=None,
    help="覆盖 OSS 外链模式: public 或 signed（默认从配置读取）",
)
@click.option(
    "--signed-url-expires",
    type=int,
    default=None,
    help="覆盖 signed URL 有效期（秒），例如 300（默认从配置读取）",
)
@click.option(
    "--json-only",
    "-j",
    is_flag=True,
    help="仅输出 JSON 格式的响应数据",
)
def send_file(
    config: Path,
    device_index: int,
    guid: str | None,
    to_username: str,
    file_path: Path,
    file_type: int,
    oss_url_mode: str | None,
    signed_url_expires: int | None,
    json_only: bool,
) -> None:
    """发送文件消息（OSS 外链 -> /cloud/upload -> /msg/send_file）"""
    wechat_config = load_wechat_config(config)
    resolved_guid, device_name = resolve_guid(wechat_config, guid=guid, device_index=device_index)

    if wechat_config.oss is None:
        msg = (
            "未配置 oss：请在 wechat.yaml 中添加 "
            "oss.endpoint/bucket/access_key_id/access_key_secret"
        )
        if json_only:
            echo_json({"success": False, "error": msg})
        else:
            click.secho(f"❌ {msg}", fg="red", err=True)
        raise SystemExit(1)

    file_size = file_path.stat().st_size
    file_md5, file_crc = _file_md5_and_crc32(file_path)
    file_name = file_path.name

    if not json_only:
        click.secho("📡 加载配置...", fg="blue")
        click.echo(f"📱 设备: {device_name}")
        click.echo(f"🔑 GUID: {resolved_guid}")
        click.echo(f"➡️  to_username: {to_username}")
        click.echo(f"📄 文件: {file_path}")
        click.echo(f"📦 大小: {file_size} bytes")
        click.echo()
        click.secho("☁️  正在上传到 OSS...", fg="blue")

    try:
        if signed_url_expires is not None:
            wechat_config.oss.signed_url_expires = signed_url_expires

        uploader = OSSUploader(wechat_config.oss)
        object_key, public_url = uploader.upload_file(file_path, url_mode=oss_url_mode)

        if not json_only:
            click.secho("✅ OSS 上传完成", fg="green")
            click.echo(f"🔗 URL: {public_url}")
            click.echo()
            click.secho("🔄 正在调用 cloud/upload...", fg="blue")

        with WeChatAPIClient(wechat_config) as client:
            upload_resp = client.cloud_upload(resolved_guid, file_type=file_type, url=public_url)
            upload_info = _parse_upload_response(upload_resp)

            if not json_only:
                click.secho("🔄 正在发送文件消息...", fg="blue")

            send_resp = client.send_file(
                guid=resolved_guid,
                to_username=to_username,
                file_id=str(upload_info["file_id"]),
                aes_key=str(upload_info["aes_key"]),
                file_size=int(file_size),
                file_md5=str(file_md5),
                file_name=str(file_name),
                file_crc=int(file_crc),
                file_key=str(upload_info.get("file_key") or ""),
            )

        if json_only:
            echo_json(
                {
                    "success": True,
                    "oss": {"object_key": object_key, "url": public_url},
                    "cloud_upload": upload_resp,
                    "send": send_resp,
                }
            )
        else:
            click.secho("✅ 发送请求完成", fg="green")
            # 输出关键字段，便于排查
            click.echo(f"file_id: {upload_info['file_id']}")
            click.echo(f"aes_key: {upload_info['aes_key']}")
            if send_resp is not None:
                echo_json(send_resp)

    except Exception as e:
        if json_only:
            echo_json({"success": False, "error": str(e)})
        else:
            click.secho(f"❌ 发送失败: {e}", fg="red", err=True)
        raise SystemExit(1) from e
