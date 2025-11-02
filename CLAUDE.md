# diting Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-01

## Active Technologies
- Python 3.12.6 (项目已安装并配置虚拟环境) + FastAPI (web框架), httpx (已有,用于调用微信API), pydantic (已有,数据验证), structlog (已有,结构化日志), uvicorn (ASGI服务器) + click (已有,CLI框架) (003-wechat-notification-webhook)
- 结构化日志文件(JSON格式),不涉及数据库存储 (003-wechat-notification-webhook)

- Python 3.12.6 (已安装并配置虚拟环境) + httpx (异步 HTTP 客户端), pydantic (数据验证), structlog (结构化日志) (001-wechat-api-connectivity)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12.6 (已安装并配置虚拟环境): Follow standard conventions

## Recent Changes
- 003-wechat-notification-webhook: Added Python 3.12.6 (项目已安装并配置虚拟环境) + FastAPI (web框架), httpx (已有,用于调用微信API), pydantic (已有,数据验证), structlog (已有,结构化日志), uvicorn (ASGI服务器) + click (已有,CLI框架)

- 001-wechat-api-connectivity: Added Python 3.12.6 (已安装并配置虚拟环境) + httpx (异步 HTTP 客户端), pydantic (数据验证), structlog (结构化日志)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
