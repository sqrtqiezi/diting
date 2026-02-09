from pathlib import Path

import click

from diting.endpoints.wechat.client import WeChatAPIClient

from .utils import echo_json, load_wechat_config, resolve_guid


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
    "--content",
    required=True,
    help="文本内容",
)
@click.option(
    "--json-only",
    "-j",
    is_flag=True,
    help="仅输出 JSON 格式的响应数据",
)
def send_text(
    config: Path,
    device_index: int,
    guid: str | None,
    to_username: str,
    content: str,
    json_only: bool,
) -> None:
    """发送文本消息（/msg/send_text）"""
    wechat_config = load_wechat_config(config)
    resolved_guid, device_name = resolve_guid(wechat_config, guid=guid, device_index=device_index)

    if not json_only:
        click.secho("📡 加载配置...", fg="blue")
        click.echo(f"📱 设备: {device_name}")
        click.echo(f"🔑 GUID: {resolved_guid}")
        click.echo(f"➡️  to_username: {to_username}")
        click.echo()
        click.secho("🔄 正在发送文本消息...", fg="blue")
        click.echo()

    try:
        with WeChatAPIClient(wechat_config) as client:
            resp = client.send_text(resolved_guid, to_username=to_username, content=content)

        if json_only:
            echo_json(resp)
        else:
            click.secho("✅ 发送请求完成", fg="green")
            if resp is not None:
                echo_json(resp)
    except Exception as e:
        if json_only:
            echo_json({"success": False, "error": str(e)})
        else:
            click.secho(f"❌ 发送失败: {e}", fg="red", err=True)
        raise SystemExit(1) from e
