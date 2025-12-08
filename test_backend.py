#!/usr/bin/env python3
"""测试后端 API 的脚本，用于调试。"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import json


def test_health_check(base_url: str = "http://localhost:8000") -> bool:
    """测试健康检查端点。"""
    print("=" * 60)
    print("测试健康检查端点")
    print("=" * 60)
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ 错误: 无法连接到后端服务")
        print(f"   请确保后端服务正在运行: {base_url}")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def main():
    """主函数。"""
    import argparse

    parser = argparse.ArgumentParser(description="测试 Excel Accelerator 后端 API")
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="后端服务地址 (默认: http://localhost:8000)",
    )

    args = parser.parse_args()

    # 测试健康检查
    if not test_health_check(args.url):
        print("\n⚠️  后端服务可能未运行，请先启动后端:")
        print("   python run_backend.py")
        print("   或")
        print("   uvicorn backend.table_render_main:app --reload")
        sys.exit(1)

    print("\n✅ 健康检查通过")


if __name__ == "__main__":
    main()

