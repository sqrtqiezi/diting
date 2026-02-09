#!/usr/bin/env python3
"""Diting CLI 工具

命令行工具,提供各种实用功能。

用法:
    python cli.py get-profile          # 获取微信登录账号信息
    python cli.py get-profile --help   # 查看帮助
"""

import json
import logging
import math
import re
import sys
from pathlib import Path

import click
import structlog
import uvicorn

from diting.cli.send import send
from diting.cli.storage import storage
from diting.endpoints.wechat.client import WeChatAPIClient
from diting.endpoints.wechat.config import WeChatConfig
from diting.endpoints.wechat.webhook_config import WebhookConfig


def _disable_logging():
    """禁用所有日志输出,避免污染 stdout"""
    # 禁用 structlog
    structlog.configure(
        processors=[],
        wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )
    # 禁用标准库 logging
    logging.basicConfig(level=logging.CRITICAL, stream=sys.stderr)


@click.group()
@click.version_option(version="0.1.0", prog_name="diting")
def cli():
    """Diting - 个人信息助手命令行工具"""
    pass


# 注册 storage 子命令组
cli.add_command(storage)
# 注册 send 子命令组
cli.add_command(send)


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


@cli.command(name="get-cdn-file")
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
    "--guid",
    "-g",
    default=None,
    help="CDN 文件 GUID (可选，默认使用配置中的设备 GUID)",
)
@click.option(
    "--json-only",
    "-j",
    is_flag=True,
    help="仅输出 JSON 格式的响应数据",
)
def get_cdn_file(config: Path, device_index: int, guid: str | None, json_only: bool):
    """获取 CDN 文件下载地址

    通过调用 /cdn/get_cdn_file 接口获取私有化云存储文件的下载地址。

    示例:
        python cli.py get-cdn-file
        python cli.py get-cdn-file --device-index 1
        python cli.py get-cdn-file --guid "your-file-guid"
        python cli.py get-cdn-file --json-only
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

    # 确定要使用的 GUID
    if guid is None:
        # 从配置文件中获取设备 GUID
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
        guid = device.guid

        if not json_only:
            click.secho("📡 加载配置...", fg="blue")
            click.echo(f"📱 设备: {device.name or '未命名设备'}")
            click.echo(f"🔑 GUID: {guid}")
    else:
        if not json_only:
            click.secho("📡 加载配置...", fg="blue")
            click.echo(f"🔑 GUID: {guid}")

    if not json_only:
        click.echo()
        click.secho("🔄 正在获取 CDN 文件下载地址...", fg="blue")
        click.echo()

    # 创建客户端并获取 CDN 文件信息
    try:
        with WeChatAPIClient(wechat_config) as client:
            # 获取原始响应数据
            request = client._build_request(
                path="/cdn/get_cdn_file",
                data={"guid": guid},
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
                click.secho("✅ 获取成功", fg="green", bold=True)
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
            click.echo("  3. 确认文件 GUID 是否有效")
            click.echo()

        sys.exit(1)


@cli.command(name="get-cdn-info")
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
def get_cdn_info(config: Path, device_index: int):
    """获取 CDN 信息

    通过调用 /cdn/get_cdn_info 接口获取设备的 CDN 信息（每 3 小时更新一次）。
    直接输出 API 返回的原始 JSON 数据。

    示例:
        python cli.py get-cdn-info
        python cli.py get-cdn-info --device-index 1
    """
    # 禁用日志输出,避免污染 stdout
    _disable_logging()

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

    # 创建客户端并获取 CDN 信息
    try:
        with WeChatAPIClient(wechat_config) as client:
            response_data = client.get_cdn_info(device.guid)

            # 检查是否成功
            if response_data.get("errcode") == 0 and "data" in response_data:
                # 成功时只输出 data 的完整内容
                click.echo(json.dumps(response_data["data"], ensure_ascii=False))
            else:
                # 失败时输出完整响应
                click.echo(json.dumps(response_data, ensure_ascii=False))

        sys.exit(0)

    except Exception as e:
        # 异常时输出到 stderr,不影响 stdout
        click.secho(f"错误: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command(name="download")
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
    "--aes-key",
    "-a",
    required=True,
    help="AES 解密密钥",
)
@click.option(
    "--file-id",
    "-i",
    required=True,
    help="文件 ID (30 开头)",
)
@click.option(
    "--file-name",
    "-f",
    required=True,
    help="文件名",
)
@click.option(
    "--file-type",
    "-t",
    type=int,
    required=True,
    help="文件类型 (整数)",
)
@click.option(
    "--json-only",
    "-j",
    is_flag=True,
    help="仅输出 JSON 格式的响应数据",
)
def download(
    config: Path,
    device_index: int,
    aes_key: str,
    file_id: str,
    file_name: str,
    file_type: int,
    json_only: bool,
):
    """通用文件下载

    通过调用 /cloud/download 接口下载文件 (适用于 30 开头的文件 ID)。
    自动从 get-cdn-info 获取 base_request 参数。

    示例:
        diting download -a "aes_key" -i "30xxx" -f "file.jpg" -t 1
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
        click.echo(f"🔑 GUID: {device.guid}")
        click.echo(f"📄 文件 ID: {file_id}")
        click.echo(f"📝 文件名: {file_name}")
        click.echo(f"📦 文件类型: {file_type}")
        click.echo()
        click.secho("🔄 正在下载文件...", fg="blue")
        click.echo()

    # 创建客户端并下载文件
    try:
        with WeChatAPIClient(wechat_config) as client:
            response_data = client.download(
                guid=device.guid,
                aes_key=aes_key,
                file_id=file_id,
                file_name=file_name,
                file_type=file_type,
            )

            if json_only:
                click.echo(json.dumps(response_data, indent=2, ensure_ascii=False))
            else:
                click.secho("=" * 80, fg="cyan")
                click.secho("📦 完整 API 响应内容", fg="cyan", bold=True)
                click.secho("=" * 80, fg="cyan")
                click.echo()
                click.echo(json.dumps(response_data, indent=2, ensure_ascii=False))
                click.echo()
                click.secho("=" * 80, fg="green")
                click.secho("✅ 下载请求完成", fg="green", bold=True)
                click.secho("=" * 80, fg="green")

        sys.exit(0)

    except Exception as e:
        if json_only:
            error_data = {"error": str(e), "success": False}
            click.echo(json.dumps(error_data, indent=2, ensure_ascii=False))
        else:
            click.secho("=" * 80, fg="red")
            click.secho("❌ 下载失败", fg="red", bold=True)
            click.secho("=" * 80, fg="red")
            click.echo()
            click.echo(f"错误信息: {e}")
            click.echo()
            click.secho("排查建议:", fg="yellow")
            click.echo("  1. 检查网络连接")
            click.echo("  2. 确认文件 ID 是否有效 (30 开头)")
            click.echo("  3. 确认 aes_key 参数是否正确")
            click.echo("  4. 确认设备 GUID 是否有效")
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
@click.option(
    "--db-path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="DuckDB 数据库路径 (启用图片 OCR 内容替换)",
)
@click.option(
    "--html",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="输出 Observability HTML 页面路径",
)
def analyze_chatrooms(
    date: str,
    parquet_root: str | None,
    config: Path | None,
    output: Path | None,
    debug_dir: Path | None,
    chatroom: tuple[str, ...],
    db_path: Path | None,
    html: Path | None,
):
    """分析群聊消息并输出话题聚合结果"""
    from diting.config import get_llm_config_path, get_messages_parquet_path
    from diting.services.llm.analysis import analyze_chatrooms_from_parquet

    if parquet_root is None:
        parquet_root = str(get_messages_parquet_path())
    if config is None:
        config = get_llm_config_path()

    db_manager = None
    if db_path is None:
        from diting.config import get_images_db_path

        db_path = get_images_db_path()
    if db_path and db_path.exists():
        from diting.services.storage.duckdb_manager import DuckDBManager

        db_manager = DuckDBManager(db_path)
        import structlog

        structlog.get_logger().info("images_db_loaded", db_path=str(db_path))

    # 清空 debug 目录
    if debug_dir:
        import shutil

        if debug_dir.exists():
            shutil.rmtree(debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)

    # 如果指定了 --html，启用 observability 收集
    enable_observability = html is not None

    results, observability_data = analyze_chatrooms_from_parquet(
        start_date=date,
        end_date=date,
        parquet_root=parquet_root,
        config_path=config,
        chatroom_ids=list(chatroom) if chatroom else None,
        debug_dir=str(debug_dir) if debug_dir else None,
        db_manager=db_manager,
        enable_observability=enable_observability,
    )

    import structlog

    log = structlog.get_logger()
    total_topics = sum(len(r.topics) for r in results)
    log.info(
        "report_render_started",
        chatrooms_count=len(results),
        total_topics=total_topics,
    )
    report = _render_markdown_report(results, date)
    log.info(
        "report_render_completed",
        report_length=len(report),
    )
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        click.echo(f"✓ 已输出 Markdown 报告到 {output}")
    else:
        click.echo(report)

    # 渲染 HTML
    if html and observability_data:
        from diting.services.llm.html_renderer import ObservabilityHtmlRenderer

        renderer = ObservabilityHtmlRenderer()
        html_content = renderer.render_multi(observability_data)
        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text(html_content, encoding="utf-8")
        click.echo(f"✓ 已输出 Observability HTML 到 {html}")


def _topic_popularity(topic) -> float:
    participants = topic.participants or []
    u_count = len(set(participants))
    m_count = int(topic.message_count)
    if u_count <= 0 or m_count <= 0:
        return 0.0
    ratio = m_count / u_count
    penalty = 1 + max(0.0, ratio - 6)
    return float(math.log(1 + u_count) ** 1.2 * math.log(1 + m_count) ** 0.8 * (1 / (penalty**0.4)))


def _render_markdown_report(results, date: str) -> str:
    lines = [
        "# 群聊消息分析报告",
        "",
        f"- 日期: {date}",
        "",
    ]

    if not results:
        lines.append("未找到可分析的群聊消息。")
        return "\n".join(lines)

    for result in results:
        topics = sorted(
            result.topics,
            key=lambda item: (_topic_popularity(item), item.message_count),
            reverse=True,
        )
        filtered_topics = [topic for topic in topics if _topic_popularity(topic) > 5]

        if not filtered_topics:
            lines.extend(["", "无热门话题。"])
            continue

        for topic in filtered_topics:
            participants = topic.participants or []
            popularity = _topic_popularity(topic)
            time_range = _format_time_range(topic.time_range)
            summary = (topic.summary or "").strip()
            lines.extend(
                [
                    "",
                    f"## {topic.title}",
                    (
                        f"🏷️ {topic.category} 🔥 {popularity:.2f} "
                        f"💬 {topic.message_count} 👥 {len(participants)}"
                    ),
                    f"🕒 {time_range}",
                    f"📝 {summary}",
                ]
            )
        lines.append("")

    return "\n".join(lines)


def _format_time_range(time_range: str) -> str:
    if not time_range:
        return "-"
    # 去掉日期，仅保留时间片段
    return re.sub(r"\d{4}-\d{2}-\d{2}\s*", "", time_range).strip()


@cli.command(name="render-report-pdf")
@click.option(
    "--input",
    "-i",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Markdown 报告路径",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="PDF 输出路径",
)
@click.option(
    "--font-path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="思源黑体字体文件路径 (可选)",
)
@click.option(
    "--font-index",
    type=int,
    default=None,
    help="字体集合文件的子字体索引 (TTC 可选)",
)
@click.option(
    "--emoji-image-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Emoji 图片目录 (Twemoji PNG，可选)",
)
@click.option(
    "--page-width",
    type=int,
    default=420,
    help="PDF 页面宽度 (pt)，适配微信阅读宽度",
)
@click.option(
    "--page-height",
    type=int,
    default=840,
    help="PDF 页面高度 (pt)",
)
@click.option(
    "--font-size",
    type=int,
    default=20,
    help="正文字体大小 (pt)",
)
def render_report_pdf(
    input_path: Path,
    output_path: Path,
    font_path: Path | None,
    font_index: int | None,
    emoji_image_dir: Path | None,
    page_width: int,
    page_height: int,
    font_size: int,
):
    """将 Markdown 报告渲染为 PDF"""
    from diting.services.report.pdf_renderer import PdfRenderOptions, render_markdown_report_pdf

    options = PdfRenderOptions(
        page_width=page_width,
        page_height=page_height,
        base_font_size=font_size,
    )
    render_markdown_report_pdf(
        markdown_path=input_path,
        output_path=output_path,
        font_path=font_path,
        font_index=font_index,
        emoji_image_dir=emoji_image_dir,
        options=options,
    )
    click.echo(f"✓ 已输出 PDF 报告到 {output_path}")


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


@cli.command(name="extract-images")
@click.option(
    "--from-username",
    "-u",
    required=True,
    help="发送者用户名 (必填)",
)
@click.option(
    "--parquet-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("data/messages/parquet"),
    help="Parquet 根目录 (默认: data/messages/parquet)",
)
@click.option(
    "--db-path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("data/metadata/images.duckdb"),
    help="DuckDB 数据库路径 (默认: data/metadata/images.duckdb)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="试运行,不修改文件",
)
def extract_images(
    from_username: str,
    parquet_root: Path,
    db_path: Path,
    dry_run: bool,
):
    """从 Parquet 消息存储中提取图片元数据

    扫描 Parquet 文件,提取指定用户发送的图片消息,
    将元数据存入 DuckDB。

    示例:
        diting extract-images -u wxid_test
        diting extract-images -u wxid_test --dry-run
    """
    from diting.services.storage.duckdb_manager import DuckDBManager
    from diting.services.storage.image_extractor import ImageExtractor

    # 显示配置信息
    click.secho("=" * 60, fg="cyan")
    click.secho("🖼️  图片提取工具", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo()
    click.echo(f"📁 Parquet 根目录: {parquet_root}")
    click.echo(f"🗄️  数据库路径: {db_path}")
    click.echo(f"👤 发送者: {from_username}")
    click.echo(f"🔬 试运行: {'是' if dry_run else '否'}")
    click.echo()

    # 检查 Parquet 目录
    if not parquet_root.exists():
        click.secho(f"❌ Parquet 目录不存在: {parquet_root}", fg="red", err=True)
        sys.exit(1)

    # 初始化 DuckDB 管理器
    db_manager = DuckDBManager(db_path)
    click.secho("✓ 数据库初始化完成", fg="green")

    # 初始化图片提取器
    extractor = ImageExtractor(
        db_manager=db_manager,
        parquet_root=parquet_root,
        dry_run=dry_run,
    )

    # 执行提取
    click.echo()
    click.secho("🔍 正在扫描 Parquet 文件...", fg="blue")

    result = extractor.extract_all(from_username, update_content=not dry_run)

    click.echo()
    click.secho("=" * 60, fg="green")
    click.secho("📊 提取结果", fg="green", bold=True)
    click.secho("=" * 60, fg="green")
    click.echo(f"📂 扫描文件数: {result.total_files_scanned}")
    click.echo(f"⏭️  跳过文件数: {result.skipped_files}")
    click.echo(f"🖼️  提取图片数: {result.total_images_extracted}")
    click.echo(f"❌ 失败文件数: {result.failed_files}")

    # 显示数据库统计
    click.echo()
    stats = db_manager.get_statistics()
    click.secho("=" * 60, fg="cyan")
    click.secho("📈 数据库统计", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo(f"🖼️  总图片数: {stats['images']['total']}")
    click.echo(f"⏳ 待下载: {stats['images']['pending']}")
    click.echo(f"✅ 已完成: {stats['images']['completed']}")
    click.echo(f"❌ 失败: {stats['images']['failed']}")
    click.echo()
    click.secho("✅ 完成!", fg="green", bold=True)


@cli.command(name="download-images")
@click.option(
    "--db-path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("data/metadata/images.duckdb"),
    help="DuckDB 数据库路径 (默认: data/metadata/images.duckdb)",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("config/wechat.yaml"),
    help="微信配置文件 (默认: config/wechat.yaml)",
)
@click.option(
    "--device-index",
    "-d",
    type=int,
    default=0,
    help="设备索引 (默认: 0)",
)
@click.option(
    "--retry",
    is_flag=True,
    help="重试之前失败的图片下载",
)
@click.option(
    "--rate-limit",
    type=int,
    default=50,
    help="每分钟最大下载次数 (默认: 50)",
)
def download_images(
    db_path: Path,
    config: Path,
    device_index: int,
    retry: bool,
    rate_limit: int,
):
    """下载待处理的图片 URL

    持续运行直到所有图片下载完成或收到 Ctrl+C 退出信号。
    支持流量限制和失败重试。

    示例:
        diting download-images
        diting download-images --retry
        diting download-images --rate-limit 30
    """
    import signal
    import time

    from diting.endpoints.wechat.config import WeChatConfig
    from diting.models.image_schema import ImageStatus
    from diting.services.storage.duckdb_manager import DuckDBManager
    from diting.services.storage.image_downloader import ImageDownloader

    # 显示配置信息
    click.secho("=" * 60, fg="cyan")
    click.secho("⬇️  图片下载工具", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo()
    click.echo(f"🗄️  数据库路径: {db_path}")
    click.echo(f"📝 配置文件: {config}")
    click.echo(f"🔄 重试模式: {'是' if retry else '否'}")
    click.echo(f"⏱️  流量限制: {rate_limit} 次/分钟")
    click.echo()

    # 检查数据库文件
    if not db_path.exists():
        click.secho(f"❌ 数据库文件不存在: {db_path}", fg="red", err=True)
        click.echo("请先运行 extract-images 命令提取图片元数据", err=True)
        sys.exit(1)

    # 加载配置
    try:
        wechat_config = WeChatConfig.load_from_yaml(config)
    except Exception as e:
        click.secho(f"❌ 配置文件加载失败: {e}", fg="red", err=True)
        sys.exit(1)

    # 初始化
    db_manager = DuckDBManager(db_path)
    downloader = ImageDownloader(
        db_manager=db_manager,
        wechat_config=wechat_config,
        device_index=device_index,
    )

    # 计算下载间隔 (毫秒)
    interval_seconds = 60.0 / rate_limit

    # 退出标志
    should_exit = False

    def signal_handler(signum, frame):
        nonlocal should_exit
        click.echo()
        click.secho("🛑 收到退出信号,正在停止...", fg="yellow")
        should_exit = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    click.secho("🚀 开始下载 (按 Ctrl+C 停止)...", fg="green")
    click.echo()

    # 统计
    total_success = 0
    total_failed = 0
    start_time = time.time()

    try:
        while not should_exit:
            # 获取待下载图片
            if retry:
                # 重试模式: 获取失败的图片
                with db_manager.get_connection() as conn:
                    rows = conn.execute(
                        """
                        SELECT image_id, msg_id, from_username, create_time,
                               aes_key, cdn_mid_img_url, status, extracted_at
                        FROM images
                        WHERE status = ?
                        ORDER BY extracted_at ASC
                        LIMIT 1
                        """,
                        [ImageStatus.FAILED.value],
                    ).fetchall()

                    if not rows:
                        click.secho("✅ 没有失败的图片需要重试", fg="green")
                        break

                    columns = [
                        "image_id",
                        "msg_id",
                        "from_username",
                        "create_time",
                        "aes_key",
                        "cdn_mid_img_url",
                        "status",
                        "extracted_at",
                    ]
                    image = dict(zip(columns, rows[0], strict=False))

                # 重置状态为 pending 再下载
                db_manager.update_image_status(image["image_id"], ImageStatus.PENDING)
            else:
                # 正常模式: 获取待下载图片
                pending = db_manager.get_pending_images(limit=1)
                if not pending:
                    click.secho("✅ 所有图片已下载完成", fg="green")
                    break
                image = pending[0]

            # 下载单张图片
            success = downloader.download_single_image(image)

            count = total_success + total_failed
            img_id = image["image_id"][:8]
            if success:
                total_success += 1
                click.echo(f"✅ [{count}] {img_id}... 下载成功")
            else:
                total_failed += 1
                click.echo(f"❌ [{count}] {img_id}... 下载失败")

            # 流量限制
            if not should_exit:
                time.sleep(interval_seconds)

    except Exception as e:
        click.secho(f"❌ 下载过程出错: {e}", fg="red", err=True)

    # 显示统计
    elapsed = time.time() - start_time
    click.echo()
    click.secho("=" * 60, fg="green")
    click.secho("📊 下载统计", fg="green", bold=True)
    click.secho("=" * 60, fg="green")
    click.echo(f"✅ 成功: {total_success}")
    click.echo(f"❌ 失败: {total_failed}")
    click.echo(f"⏱️  耗时: {elapsed:.1f} 秒")

    # 显示数据库统计
    stats = db_manager.get_statistics()
    click.echo()
    click.secho("=" * 60, fg="cyan")
    click.secho("📈 数据库统计", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo(f"🖼️  总图片数: {stats['images']['total']}")
    click.echo(f"⏳ 待下载: {stats['images']['pending']}")
    click.echo(f"✅ 已完成: {stats['images']['completed']}")
    click.echo(f"❌ 失败: {stats['images']['failed']}")
    click.echo()
    click.secho("✅ 完成!", fg="green", bold=True)


@cli.command(name="process-ocr")
@click.option(
    "--db-path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("data/metadata/images.duckdb"),
    help="DuckDB 数据库路径 (默认: data/metadata/images.duckdb)",
)
@click.option(
    "--rate-limit",
    type=int,
    default=30,
    help="每分钟最大处理次数 (默认: 30)",
)
def process_ocr(db_path: Path, rate_limit: int):
    """处理图片 OCR 识别

    从 images 表读取已下载但未 OCR 处理的图片，
    调用阿里云 OCR API 进行识别。

    需要设置环境变量:
        ALIYUN_ACCESS_KEY_ID
        ALIYUN_ACCESS_KEY_SECRET

    示例:
        diting process-ocr
        diting process-ocr --rate-limit 20
    """
    import os
    import signal
    import time

    from diting.services.storage.duckdb_manager import DuckDBManager
    from diting.services.storage.image_ocr_processor import ImageOCRProcessor

    # 检查环境变量
    access_key_id = os.environ.get("ALIYUN_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIYUN_ACCESS_KEY_SECRET")

    if not access_key_id or not access_key_secret:
        click.secho(
            "❌ 请设置环境变量 ALIYUN_ACCESS_KEY_ID 和 ALIYUN_ACCESS_KEY_SECRET",
            fg="red",
            err=True,
        )
        sys.exit(1)

    # 显示配置信息
    click.secho("=" * 60, fg="cyan")
    click.secho("🔍 图片 OCR 处理工具", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo()
    click.echo(f"🗄️  数据库路径: {db_path}")
    click.echo(f"⏱️  流量限制: {rate_limit} 次/分钟")
    click.echo()

    # 检查数据库文件
    if not db_path.exists():
        click.secho(f"❌ 数据库文件不存在: {db_path}", fg="red", err=True)
        click.echo("请先运行 extract-images 和 download-images 命令", err=True)
        sys.exit(1)

    # 初始化
    db_manager = DuckDBManager(db_path)
    processor = ImageOCRProcessor(
        db_manager=db_manager,
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
    )

    # 计算处理间隔
    interval_seconds = 60.0 / rate_limit

    # 退出标志
    should_exit = False

    def signal_handler(signum, frame):
        nonlocal should_exit
        click.echo()
        click.secho("🛑 收到退出信号,正在停止...", fg="yellow")
        should_exit = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    click.secho("🚀 开始 OCR 处理 (按 Ctrl+C 停止)...", fg="green")
    click.echo()

    # 统计
    total_success = 0
    total_failed = 0
    with_text = 0
    without_text = 0
    start_time = time.time()

    try:
        while not should_exit:
            # 获取待处理图片
            pending = db_manager.get_pending_ocr_images(limit=1)

            if not pending:
                click.secho("✅ 所有图片 OCR 处理完成", fg="green")
                break

            image = pending[0]
            success, has_text_result = processor.process_single_image(image)

            count = total_success + total_failed
            img_id = image["image_id"][:8]
            if success:
                total_success += 1
                if has_text_result:
                    with_text += 1
                    click.echo(f"📝 [{count}] {img_id}... 有文字")
                else:
                    without_text += 1
                    click.echo(f"🖼️  [{count}] {img_id}... 无文字")
            else:
                total_failed += 1
                click.echo(f"❌ [{count}] {img_id}... 处理失败")

            # 流量限制
            if not should_exit:
                time.sleep(interval_seconds)

    except Exception as e:
        click.secho(f"❌ OCR 处理过程出错: {e}", fg="red", err=True)

    # 显示统计
    elapsed = time.time() - start_time
    click.echo()
    click.secho("=" * 60, fg="green")
    click.secho("📊 OCR 处理统计", fg="green", bold=True)
    click.secho("=" * 60, fg="green")
    click.echo(f"✅ 成功: {total_success}")
    click.echo(f"❌ 失败: {total_failed}")
    click.echo(f"📝 有文字: {with_text}")
    click.echo(f"🖼️  无文字: {without_text}")
    click.echo(f"⏱️  耗时: {elapsed:.1f} 秒")
    click.echo()
    click.secho("✅ 完成!", fg="green", bold=True)


if __name__ == "__main__":
    cli()
