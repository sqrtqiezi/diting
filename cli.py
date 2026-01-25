#!/usr/bin/env python3
"""Diting CLI 工具

命令行工具,提供各种实用功能。

用法:
    python cli.py get-profile          # 获取微信登录账号信息
    python cli.py get-profile --help   # 查看帮助
"""

import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

import click
import uvicorn
from diting.endpoints.wechat.client import WeChatAPIClient
from diting.endpoints.wechat.config import WeChatConfig
from diting.endpoints.wechat.webhook_config import WebhookConfig


@click.group()
@click.version_option(version="0.1.0", prog_name="diting")
def cli():
    """Diting - 个人信息助手命令行工具"""
    pass


@cli.command(name="get-profile")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("config/wechat.yaml"),
    help="配置文件路径 (默认: config/wechat.yaml)",
)
@click.option(
    "--device-index",
    "-d",
    type=int,
    default=0,
    help="设备索引 (默认: 0 - 第一个设备)",
)
@click.option(
    "--json-only",
    "-j",
    is_flag=True,
    help="仅输出 JSON 格式的响应数据",
)
def get_profile(config: Path, device_index: int, json_only: bool):
    """获取微信登录账号信息

    通过调用微信 API 的 /user/get_profile 接口获取当前登录账号的信息。

    示例:
        python cli.py get-profile
        python cli.py get-profile --config config/wechat.yaml
        python cli.py get-profile --device-index 1
        python cli.py get-profile --json-only
    """
    # 加载配置
    if not config.exists():
        click.secho(f"❌ 配置文件不存在: {config}", fg="red", err=True)
        click.echo("请先创建配置文件,参考: config/wechat.yaml.example", err=True)
        sys.exit(1)

    try:
        wechat_config = WeChatConfig.load_from_yaml(config)
    except Exception as e:
        click.secho(f"❌ 配置文件加载失败: {e}", fg="red", err=True)
        sys.exit(1)

    # 检查设备配置
    if not wechat_config.devices:
        click.secho("❌ 配置中没有设备信息", fg="red", err=True)
        click.echo("请在 config/wechat.yaml 的 devices 部分添加设备 GUID", err=True)
        sys.exit(1)

    if device_index >= len(wechat_config.devices):
        click.secho(
            f"❌ 设备索引 {device_index} 超出范围 (共 {len(wechat_config.devices)} 个设备)",
            fg="red",
            err=True,
        )
        sys.exit(1)

    device = wechat_config.devices[device_index]

    if not json_only:
        click.secho("📡 加载配置...", fg="blue")
        click.echo(f"📱 设备: {device.name or '未命名设备'}")
        click.echo(f"🔑 设备 ID: {device.guid}")
        click.echo()
        click.secho("🔄 正在获取登录账号信息...", fg="blue")
        click.echo()

    # 创建客户端并获取用户信息
    try:
        with WeChatAPIClient(wechat_config) as client:
            # 使用 get_profile 方法
            user_info = client.get_profile(device.guid)

            # 获取原始响应数据用于显示
            request = client._build_request(
                path="/user/get_profile",
                data={"guid": device.guid},
            )
            response_data = client._send_request(request)

            if json_only:
                # 仅输出 JSON
                click.echo(json.dumps(response_data, indent=2, ensure_ascii=False))
            else:
                # 详细输出
                click.secho("=" * 80, fg="cyan")
                click.secho("📦 完整 API 响应内容", fg="cyan", bold=True)
                click.secho("=" * 80, fg="cyan")
                click.echo()
                click.echo(json.dumps(response_data, indent=2, ensure_ascii=False))
                click.echo()

                click.secho("=" * 80, fg="green")
                click.secho("✅ 解析后的用户信息", fg="green", bold=True)
                click.secho("=" * 80, fg="green")
                click.echo()
                click.echo(f"微信 ID:    {user_info.wechat_id}")
                click.echo(f"昵称:       {user_info.nickname}")
                if user_info.avatar:
                    click.echo(f"头像 URL:   {user_info.avatar}")
                click.echo()
                click.secho("=" * 80, fg="green")

            sys.exit(0)

    except Exception as e:
        if json_only:
            # JSON 模式下也输出错误
            error_data = {"error": str(e), "success": False}
            click.echo(json.dumps(error_data, indent=2, ensure_ascii=False))
        else:
            click.secho("=" * 80, fg="red")
            click.secho("❌ 获取失败", fg="red", bold=True)
            click.secho("=" * 80, fg="red")
            click.echo()
            click.echo(f"错误信息: {e}")
            click.echo()
            click.secho("排查建议:", fg="yellow")
            click.echo("  1. 检查网络连接")
            click.echo("  2. 确认 app_key 和 app_secret 是否正确")
            click.echo("  3. 确认设备 GUID 是否有效")
            click.echo("  4. 检查设备是否在线")
            click.echo()

        sys.exit(1)


@cli.command(name="analyze-chatrooms")
@click.option(
    "--date",
    "-d",
    required=True,
    help="分析日期 (YYYY-MM-DD)",
)
@click.option(
    "--parquet-root",
    default=None,
    help="Parquet 根目录 (默认从配置读取)",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="LLM 配置文件路径 (默认: config/llm.yaml)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="输出文件路径 (JSONL)",
)
@click.option(
    "--debug-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="输出批次调试信息目录",
)
@click.option(
    "--chatroom",
    "-r",
    multiple=True,
    help="限定分析的群聊 ID（可重复传入）",
)
def analyze_chatrooms(
    date: str,
    parquet_root: str | None,
    config: Path | None,
    output: Path | None,
    debug_dir: Path | None,
    chatroom: tuple[str, ...],
):
    """分析群聊消息并输出话题聚合结果"""
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from src.config import get_llm_config_path, get_messages_parquet_path
    from src.services.llm.analysis import analyze_chatrooms_from_parquet

    if parquet_root is None:
        parquet_root = str(get_messages_parquet_path())
    if config is None:
        config = get_llm_config_path()

    results = analyze_chatrooms_from_parquet(
        start_date=date,
        end_date=date,
        parquet_root=parquet_root,
        config_path=config,
        chatroom_ids=list(chatroom) if chatroom else None,
        debug_dir=str(debug_dir) if debug_dir else None,
    )

    report = _render_markdown_report(results, date)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        click.echo(f"✓ 已输出 Markdown 报告到 {output}")
    else:
        click.echo(report)


def _topic_popularity(topic) -> float:
    participants = topic.participants or []
    u_count = len(set(participants))
    m_count = int(topic.message_count)
    if u_count <= 0 or m_count <= 0:
        return 0.0
    ratio = m_count / u_count
    penalty = 1 + max(0.0, ratio - 6)
    return math.log(1 + u_count) ** 1.2 * math.log(1 + m_count) ** 0.8 * (1 / (penalty**0.4))


def _render_markdown_report(results, date: str) -> str:
    created_at = datetime.now().isoformat(timespec="seconds")
    lines = [
        "# 群聊消息分析报告",
        "",
        f"- 分析日期: {date}",
        f"- 生成时间: {created_at}",
        "",
    ]

    if not results:
        lines.append("未找到可分析的群聊消息。")
        return "\n".join(lines)

    for result in results:
        chatroom_title = result.chatroom_name or result.chatroom_id
        lines.extend([f"## 群聊: {chatroom_title}", ""])
        if chatroom_title != result.chatroom_id:
            lines.append(f"- 群聊 ID: {result.chatroom_id}")
        lines.extend(
            [
                f"- 消息总数: {result.total_messages}",
                f"- 话题总数: {len(result.topics)}",
                "",
                "### 热门话题 Top 10",
                "",
                "| 排名 | 话题 | 分类 | 热门度 | 消息数 | 参与人数 | 时间范围 |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )

        topics = sorted(
            result.topics,
            key=lambda item: (_topic_popularity(item), item.message_count),
            reverse=True,
        )
        top_topics = topics[:10]

        if not top_topics:
            lines.append("| 1 | 无 | 无 | 0 | 0 | 0 | - |")
            lines.append("")
            continue

        for idx, topic in enumerate(top_topics, start=1):
            participants = topic.participants or []
            popularity = _topic_popularity(topic)
            time_range = _format_time_range(topic.time_range)
            row_template = (
                "| {idx} | {title} | {category} | {popularity:.2f} | "
                "{count} | {people} | {time} |"
            )
            lines.append(
                row_template.format(
                    idx=idx,
                    title=topic.title,
                    category=topic.category,
                    popularity=popularity,
                    count=topic.message_count,
                    people=len(participants),
                    time=time_range,
                )
            )

        lines.append("")
        lines.append("### 话题摘要")
        lines.append("")
        for idx, topic in enumerate(top_topics, start=1):
            summary = (topic.summary or "").strip()
            lines.append(f"{idx}. {topic.title}: {summary}")
        lines.append("")

    return "\n".join(lines)


def _format_time_range(time_range: str) -> str:
    if not time_range:
        return "-"
    # 去掉日期，仅保留时间片段
    return re.sub(r"\d{4}-\d{2}-\d{2}\s*", "", time_range).strip()


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Configuration file path (YAML)",
)
@click.option(
    "--host",
    "-h",
    type=str,
    help="Host to bind (default: 0.0.0.0)",
)
@click.option(
    "--port",
    "-p",
    type=int,
    help="Port to bind (default: 8000)",
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Log level (default: INFO)",
)
def serve(config, host, port, log_level):
    """启动 Webhook 服务

    启动 FastAPI webhook 服务,用于接收来自第三方微信转发服务的消息推送。

    示例:
        python cli.py serve
        python cli.py serve --port 9000
        python cli.py serve --host 127.0.0.1 --port 8888
        python cli.py serve --log-level DEBUG
    """
    # 加载配置
    webhook_config = WebhookConfig()

    # 命令行参数覆盖配置文件
    if host:
        webhook_config.host = host
    if port:
        webhook_config.port = port
    if log_level:
        webhook_config.log_level = log_level.upper()

    # 显示启动信息
    click.secho("=" * 60, fg="cyan")
    click.secho(
        f"🚀 {webhook_config.service_name} v{webhook_config.service_version}",
        fg="cyan",
        bold=True,
    )
    click.secho("=" * 60, fg="cyan")
    click.echo()
    click.echo(f"📡 Host:          {webhook_config.host}")
    click.echo(f"🔌 Port:          {webhook_config.port}")
    click.echo(f"📝 Log Level:     {webhook_config.log_level}")
    click.echo(f"📄 Log File:      {webhook_config.log_file}")
    click.echo(f"🎯 Webhook Path:  {webhook_config.webhook_path}")
    click.echo(f"💚 Health Check:  {webhook_config.health_check_path}")
    click.echo()
    click.secho("=" * 60, fg="cyan")
    click.secho("🏁 Starting server... (Press Ctrl+C to stop)", fg="green")
    click.secho("=" * 60, fg="cyan")
    click.echo()

    # 启动 uvicorn 服务器
    try:
        uvicorn.run(
            "diting.endpoints.wechat.webhook_app:app",
            host=webhook_config.host,
            port=webhook_config.port,
            log_level=webhook_config.log_level.lower(),
            access_log=False,  # 我们使用自己的结构化日志
        )
    except KeyboardInterrupt:
        click.echo()
        click.secho("🛑 Server stopped by user", fg="yellow")
        sys.exit(0)


if __name__ == "__main__":
    cli()
