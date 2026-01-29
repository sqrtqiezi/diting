#!/usr/bin/env python3
"""阿里云 OCR 快速测试脚本

测试 RecognizeGeneral API 的接入，验证 OCR 服务可用性。

使用方法:
    # 设置环境变量
    export ALIYUN_ACCESS_KEY_ID="your_access_key_id"
    export ALIYUN_ACCESS_KEY_SECRET="your_access_key_secret"

    # 运行测试
    uv run python scripts/test_aliyun_ocr.py [image_url]
"""

import os
import sys

from alibabacloud_ocr_api20210707 import models as ocr_models
from alibabacloud_ocr_api20210707.client import Client
from alibabacloud_tea_openapi import models as open_api_models

# 默认测试图片
DEFAULT_IMAGE_URL = "https://diting-assets2.oss-cn-shanghai.aliyuncs.com/wecdn/2026-01-29/15686c4c8086812db5063f7239aa614a_b6347be0-2431-42b9-8ee9-b134514e7dec.jpg"


def main() -> None:
    # 从环境变量读取凭证
    access_key_id = os.environ.get("ALIYUN_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIYUN_ACCESS_KEY_SECRET")

    if not access_key_id or not access_key_secret:
        print("错误: 请设置环境变量 ALIYUN_ACCESS_KEY_ID 和 ALIYUN_ACCESS_KEY_SECRET")
        print("\n示例:")
        print('  export ALIYUN_ACCESS_KEY_ID="your_access_key_id"')
        print('  export ALIYUN_ACCESS_KEY_SECRET="your_access_key_secret"')
        sys.exit(1)

    # 获取图片 URL (命令行参数或默认值)
    image_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE_URL

    # 创建客户端
    config = open_api_models.Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        endpoint="ocr-api.cn-hangzhou.aliyuncs.com",
    )
    client = Client(config)

    # 调用 OCR API
    print(f"正在识别图片: {image_url[:50]}...")
    request = ocr_models.RecognizeGeneralRequest(url=image_url)
    response = client.recognize_general(request)

    print(f"\nRequest ID: {response.body.request_id}")
    print(f"识别结果: {response.body.data}")


if __name__ == "__main__":
    main()
