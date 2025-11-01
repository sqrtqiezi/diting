#!/usr/bin/env python3
"""微信 API 连通性测试工具

快速测试微信 API 配置和连接状态。

使用方法:
    python src/diting/cli/wechat_test.py --config config/wechat.yaml
"""

import argparse
import sys
from pathlib import Path

from diting.endpoints.wechat.client import WeChatAPIClient
from diting.endpoints.wechat.config import WeChatConfig
from diting.endpoints.wechat.exceptions import WeChatAPIError
from diting.utils.logging import configure_logging, get_logger
from diting.utils.security import mask_secret

# 彩色输出(ANSI 转义码)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_success(message: str) -> None:
    """打印成功消息"""
    print(f"{GREEN}✅ {message}{RESET}")


def print_error(message: str) -> None:
    """打印错误消息"""
    print(f"{RED}❌ {message}{RESET}")


def print_warning(message: str) -> None:
    """打印警告消息"""
    print(f"{YELLOW}⚠️  {message}{RESET}")


def print_info(message: str) -> None:
    """打印信息消息"""
    print(f"{BLUE}📡 {message}{RESET}")


def test_wechat_api(config_path: Path) -> int:
    """测试微信 API 连通性

    Args:
        config_path: 配置文件路径

    Returns:
        int: 退出码 (0=成功, 1=失败)
    """
    logger = get_logger(__name__)

    # 1. 加载配置
    print_info(f"加载配置文件: {config_path}")

    try:
        config = WeChatConfig.load_from_yaml(config_path)
    except FileNotFoundError:
        print_error(f"配置文件不存在: {config_path}")
        return 1
    except Exception as e:
        print_error(f"加载配置失败: {e}")
        return 1

    print_success("配置加载成功")
    print(f"  API URL: {config.api.base_url}")
    print(f"  App Key: {mask_secret(config.api.app_key)}")
    print(f"  App Secret: {mask_secret(config.api.app_secret)}")
    print(f"  设备数量: {len(config.devices)}")
    print()

    # 2. 检查设备列表
    if not config.devices:
        print_warning("配置中没有设备,无法测试 API 连接")
        return 1

    # 3. 创建客户端
    print_info("初始化 API 客户端")

    try:
        with WeChatAPIClient(config) as client:
            print_success("客户端初始化成功")
            print()

            # 4. 测试每个设备
            for i, device in enumerate(config.devices, 1):
                print_info(f"测试设备 {i}/{len(config.devices)}: {device.name or device.guid}")

                try:
                    user_info = client.get_user_info(device.guid)

                    print_success(f"API 连接测试成功!")
                    print(f"  设备 ID: {device.guid}")
                    print(f"  微信号: {user_info.wechat_id}")
                    print(f"  昵称: {user_info.nickname}")
                    if user_info.avatar:
                        print(f"  头像: {user_info.avatar}")
                    print()

                except WeChatAPIError as e:
                    print_error(f"设备测试失败: {e}")
                    print(f"  错误代码: {e.error_code}")
                    print()
                    continue

            print_success("所有测试完成!")
            return 0

    except WeChatAPIError as e:
        print_error(f"API 错误: {e}")
        logger.error("api_test_failed", error=str(e), error_code=e.error_code)
        return 1

    except Exception as e:
        print_error(f"未知错误: {e}")
        logger.error("unexpected_error", error=str(e))
        return 1


def main() -> None:
    """CLI 入口点"""
    parser = argparse.ArgumentParser(
        description="微信 API 连通性测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python src/diting/cli/wechat_test.py --config config/wechat.yaml
  python src/diting/cli/wechat_test.py -c config/wechat.yaml --verbose
        """,
    )

    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("config/wechat.yaml"),
        help="配置文件路径 (默认: config/wechat.yaml)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="启用详细日志输出",
    )

    args = parser.parse_args()

    # 配置日志
    log_level = "DEBUG" if args.verbose else "INFO"
    configure_logging(level=log_level, json_format=False)

    # 执行测试
    exit_code = test_wechat_api(args.config)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
