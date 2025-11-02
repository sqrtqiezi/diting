"""
命令行工具模块

提供 Diting webhook 服务的 CLI 管理命令。
"""

import click
import uvicorn

from diting.endpoints.wechat.webhook_config import WebhookConfig


@click.group()
@click.version_option(version="1.0.0", prog_name="diting")
def cli():
    """Diting WeChat Webhook Service CLI"""
    pass


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
    """
    Start the webhook service

    Examples:
        diting serve
        diting serve --port 9000
        diting serve --host 127.0.0.1 --port 8888
        diting serve --config config/webhook.yaml
        diting serve --log-level DEBUG
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
    click.echo(f"Starting {webhook_config.service_name} v{webhook_config.service_version}")
    click.echo(f"Host: {webhook_config.host}")
    click.echo(f"Port: {webhook_config.port}")
    click.echo(f"Log Level: {webhook_config.log_level}")
    click.echo(f"Log File: {webhook_config.log_file}")
    click.echo(f"Webhook Path: {webhook_config.webhook_path}")
    click.echo("-" * 50)

    # 启动 uvicorn 服务器
    uvicorn.run(
        "diting.endpoints.wechat.webhook_app:app",
        host=webhook_config.host,
        port=webhook_config.port,
        log_level=webhook_config.log_level.lower(),
        access_log=False,  # 我们使用自己的结构化日志
    )


if __name__ == "__main__":
    cli()
