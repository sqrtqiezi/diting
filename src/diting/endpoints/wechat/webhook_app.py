"""
FastAPI Webhook Application

提供微信消息 webhook 接收端点和健康检查端点。
"""

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .webhook_config import WebhookConfig
from .webhook_handler import WebhookRequest, log_webhook_request
from .webhook_logger import check_log_writable, setup_webhook_logger

# 全局状态
app_state = {"start_time": 0.0, "message_count": 0, "config": None}


class HealthStatus(BaseModel):
    """健康状态模型"""

    status: str  # "healthy" | "unhealthy"
    version: str
    uptime_seconds: int = 0
    message_count: int = 0
    log_writable: bool = True
    error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    config = WebhookConfig()
    app_state["config"] = config
    app_state["start_time"] = time.time()

    # 配置日志
    setup_webhook_logger(
        log_file=config.log_file,
        max_bytes=config.log_max_size_mb * 1024 * 1024,
        backup_count=config.log_backup_count,
        log_level=config.log_level,
    )

    print(f"Starting {config.service_name} v{config.service_version}...")
    print(f"Logging to: {config.log_file}")
    print(f"Webhook endpoint: {config.webhook_path}")
    print(f"Health check: {config.health_check_path}")

    yield

    # 关闭时
    uptime = time.time() - app_state["start_time"]
    print(f"Stopping {config.service_name}... (uptime: {uptime:.1f}s)")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="Diting Webhook Service",
    description="WeChat notification webhook receiver",
    version="1.0.0",
    lifespan=lifespan,
)


# Webhook 响应模型
class WebhookResponse(BaseModel):
    """Webhook 响应模型"""

    status: str = "ok"
    request_id: str


# POST /webhook/wechat 端点
@app.post("/webhook/wechat", response_model=WebhookResponse)
async def receive_wechat_message(request: Request, background_tasks: BackgroundTasks):
    """
    接收微信通知消息 webhook

    - 立即返回 200 OK (< 100ms)
    - 后台异步记录到日志
    - 接受任意格式:JSON, Form, Text, Binary
    """
    # 读取原始请求体
    body_bytes = await request.body()

    # 创建 WebhookRequest 对象
    webhook_request = WebhookRequest(
        client_ip=request.client.host if request.client else "unknown",
        method=request.method,
        path=str(request.url.path),
        headers=dict(request.headers),
        body_bytes_length=len(body_bytes),
        content_type=request.headers.get("content-type"),
    )

    # 后台任务:记录日志
    background_tasks.add_task(log_webhook_request, webhook_request, body_bytes)

    # 递增消息计数器
    app_state["message_count"] += 1

    # 立即返回成功响应
    return WebhookResponse(request_id=webhook_request.request_id)


# GET /health 端点
@app.get("/health", response_model=HealthStatus)
async def health_check():
    """
    健康检查端点

    返回服务健康状态,包括:
    - 服务状态(healthy/unhealthy)
    - 版本信息
    - 运行时间(秒)
    - 已处理消息数量
    - 日志文件可写性

    Returns:
        HealthStatus: 健康状态模型
        - 200: 服务健康
        - 503: 服务不可用(日志写入失败)
    """
    config = app_state["config"]

    # 计算运行时间
    uptime_seconds = int(time.time() - app_state["start_time"])

    # 检查日志文件可写性
    log_writable, error_message = check_log_writable(config.log_file)

    # 构建响应
    health_status = HealthStatus(
        status="healthy" if log_writable else "unhealthy",
        version=config.service_version,
        uptime_seconds=uptime_seconds,
        message_count=app_state["message_count"],
        log_writable=log_writable,
        error=error_message,
    )

    # 如果不健康,返回 503 状态码
    if not log_writable:
        return JSONResponse(
            status_code=503,
            content=health_status.model_dump(),
        )

    return health_status


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器 - 捕获所有未处理的异常"""
    logger = structlog.get_logger("webhook")
    logger.error(
        "unhandled_exception",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "error_type": type(exc).__name__,
        },
    )
