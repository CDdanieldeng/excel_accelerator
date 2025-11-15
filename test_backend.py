#!/usr/bin/env python3
"""测试后端 API 的脚本，用于调试。"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from typing import Optional


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


def test_guess_table(
    file_path: str,
    base_url: str = "http://localhost:8000",
    max_preview_rows: int = 50,
    max_scan_rows: int = 200,
) -> Optional[dict]:
    """测试表头猜测 API。"""
    print("\n" + "=" * 60)
    print("测试表头猜测 API")
    print("=" * 60)

    if not os.path.exists(file_path):
        print(f"❌ 错误: 文件不存在: {file_path}")
        return None

    file_name = os.path.basename(file_path)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"文件: {file_name}")
    print(f"大小: {file_size_mb:.2f} MB")
    print(f"预览行数: {max_preview_rows}")
    print(f"扫描行数: {max_scan_rows}")

    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_name, f, "application/octet-stream")}
            params = {
                "max_preview_rows": max_preview_rows,
                "max_scan_rows": max_scan_rows,
            }

            print("\n发送请求...")
            response = requests.post(
                f"{base_url}/api/guess_table",
                files=files,
                params=params,
                timeout=300,  # 5 分钟超时
            )

            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("\n✅ 成功!")
                print("\n结果摘要:")
                print(f"  文件类型: {result['file_type']}")
                print(f"  Sheet 数量: {len(result['sheets'])}")

                for i, sheet in enumerate(result["sheets"], 1):
                    print(f"\n  Sheet {i}: {sheet['name']}")
                    print(f"    主表: {'是' if sheet['is_main'] else '否'}")
                    print(f"    表头行: 第 {sheet['header_row_index'] + 1} 行 (索引: {sheet['header_row_index']})")
                    print(f"    数据起始行: 第 {sheet['data_start_row_index'] + 1} 行 (索引: {sheet['data_start_row_index']})")
                    print(f"    检测到的列数: {len(sheet['detected_columns'])}")
                    if sheet['detected_columns']:
                        print(f"    列名: {', '.join(sheet['detected_columns'][:5])}")
                        if len(sheet['detected_columns']) > 5:
                            print(f"            ... (共 {len(sheet['detected_columns'])} 列)")

                # 保存完整结果到文件
                output_file = f"test_result_{file_name}.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"\n完整结果已保存到: {output_file}")

                return result
            else:
                print("\n❌ 请求失败")
                try:
                    error_data = response.json()
                    print(f"错误信息: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    print(f"响应内容: {response.text}")
                return None

    except requests.exceptions.ConnectionError:
        print("❌ 错误: 无法连接到后端服务")
        print(f"   请确保后端服务正在运行: {base_url}")
        return None
    except requests.exceptions.Timeout:
        print("❌ 错误: 请求超时")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数。"""
    import argparse

    parser = argparse.ArgumentParser(description="测试 Excel Accelerator 后端 API")
    parser.add_argument(
        "--file",
        type=str,
        help="要测试的文件路径",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="后端服务地址 (默认: http://localhost:8000)",
    )
    parser.add_argument(
        "--max-preview-rows",
        type=int,
        default=50,
        help="最大预览行数 (默认: 50)",
    )
    parser.add_argument(
        "--max-scan-rows",
        type=int,
        default=200,
        help="最大扫描行数 (默认: 200)",
    )
    parser.add_argument(
        "--health-only",
        action="store_true",
        help="只测试健康检查端点",
    )

    args = parser.parse_args()

    # 测试健康检查
    if not test_health_check(args.url):
        print("\n⚠️  后端服务可能未运行，请先启动后端:")
        print("   python run_backend.py")
        print("   或")
        print("   uvicorn backend.main:app --reload")
        sys.exit(1)

    # 如果只测试健康检查，退出
    if args.health_only:
        print("\n✅ 健康检查通过")
        sys.exit(0)

    # 测试表头猜测
    if args.file:
        test_guess_table(
            args.file,
            args.url,
            args.max_preview_rows,
            args.max_scan_rows,
        )
    else:
        print("\n⚠️  请提供要测试的文件路径:")
        print("   python test_backend.py --file <文件路径>")
        print("\n示例:")
        print("   python test_backend.py --file test.xlsx")
        print("   python test_backend.py --file data.csv --max-preview-rows 100")


if __name__ == "__main__":
    main()

