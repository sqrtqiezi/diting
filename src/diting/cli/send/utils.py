import json
from pathlib import Path

import click

from diting.endpoints.wechat.config import WeChatConfig


def load_wechat_config(config: Path) -> WeChatConfig:
    if not config.exists():
        click.secho(f"❌ 配置文件不存在: {config}", fg="red", err=True)
        click.echo("请先创建配置文件,参考: config/wechat.yaml.example", err=True)
        raise SystemExit(1)

    try:
        return WeChatConfig.load_from_yaml(config)
    except Exception as e:
        click.secho(f"❌ 配置文件加载失败: {e}", fg="red", err=True)
        raise SystemExit(1) from e


def resolve_guid(
    wechat_config: WeChatConfig, *, guid: str | None, device_index: int
) -> tuple[str, str]:
    """返回 (guid, display_name)。"""
    if guid:
        return guid, "自定义 GUID"

    if not wechat_config.devices:
        click.secho("❌ 配置中没有设备信息", fg="red", err=True)
        click.echo("请在 config/wechat.yaml 的 devices 部分添加设备 GUID", err=True)
        raise SystemExit(1)

    if device_index >= len(wechat_config.devices):
        click.secho(
            f"❌ 设备索引 {device_index} 超出范围 (共 {len(wechat_config.devices)} 个设备)",
            fg="red",
            err=True,
        )
        raise SystemExit(1)

    device = wechat_config.devices[device_index]
    return device.guid, device.name or "未命名设备"


def echo_json(data: object, *, indent: int = 2) -> None:
    click.echo(json.dumps(data, indent=indent, ensure_ascii=False))
