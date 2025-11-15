#!/usr/bin/env python3
"""测试 Sheet 图片渲染 API 的脚本。"""

import sys
import os
import base64
import io
import requests
from pathlib import Path
from PIL import Image

# Backend API URL
BACKEND_URL = "http://localhost:8000"


def test_sheet_image(
    file_path: str,
    sheet_name: str = "Sheet1",
    row_start: int = 0,
    row_end: int = 10,
    col_start: int = 0,
    col_end: int = 5,
    save_image: bool = True,
) -> None:
    """
    测试 Sheet 图片渲染 API。

    Args:
        file_path: 文件路径
        sheet_name: Sheet 名称
        row_start: 起始行
        row_end: 结束行
        col_start: 起始列
        col_end: 结束列
        save_image: 是否保存图片
    """
    print("=" * 60)
    print("测试 Sheet 图片渲染 API")
    print("=" * 60)
    print(f"文件路径: {file_path}")
    print(f"Sheet 名称: {sheet_name}")
    print(f"行范围: [{row_start}, {row_end}]")
    print(f"列范围: [{col_start}, {col_end}]")
    print("-" * 60)

    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 错误: 文件不存在: {file_path}")
        print(f"   当前工作目录: {os.getcwd()}")
        print(f"   请使用绝对路径或确保文件存在")
        return

    try:
        # 发送请求
        params = {
            "file_path": file_path,
            "sheet_name": sheet_name,
            "row_start": row_start,
            "row_end": row_end,
            "col_start": col_start,
            "col_end": col_end,
        }

        print("发送请求...")
        response = requests.get(
            f"{BACKEND_URL}/api/sheet_image",
            params=params,
            timeout=60,
        )

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            # 解码图片
            image_base64 = result["image_base64"]
            image_bytes = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_bytes))

            print("\n✅ 成功!")
            print(f"图片大小: {image.width} x {image.height} 像素")
            print(f"行高: {result['row_height_px']} 像素")
            print(f"列宽: {result['col_width_px']} 像素")
            print(f"图片数据大小: {len(image_bytes)} 字节")

            # 保存图片
            if save_image:
                output_file = "sheet_image_output.png"
                image.save(output_file)
                print(f"\n📸 图片已保存到: {output_file}")

            # 显示元信息
            print("\n📊 元信息:")
            print(f"  Sheet 名称: {result['sheet_name']}")
            print(f"  行范围: [{result['row_start']}, {result['row_end']}]")
            print(f"  列范围: [{result['col_start']}, {result['col_end']}]")

        else:
            print("\n❌ 请求失败")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data}")
            except:
                print(f"响应内容: {response.text}")

    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到后端服务")
        print(f"   请确保后端服务正在运行: {BACKEND_URL}")
        print(f"   启动命令: python run_backend.py")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数。"""
    import argparse

    parser = argparse.ArgumentParser(description="测试 Sheet 图片渲染 API")
    parser.add_argument(
        "file_path",
        type=str,
        help="文件路径",
    )
    parser.add_argument(
        "--sheet",
        type=str,
        default="Sheet1",
        help="Sheet 名称 (默认: Sheet1, CSV 使用 '__default__')",
    )
    parser.add_argument(
        "--row-start",
        type=int,
        default=0,
        help="起始行 (0-based, 默认: 0)",
    )
    parser.add_argument(
        "--row-end",
        type=int,
        default=10,
        help="结束行 (0-based, 默认: 10)",
    )
    parser.add_argument(
        "--col-start",
        type=int,
        default=0,
        help="起始列 (0-based, 默认: 0)",
    )
    parser.add_argument(
        "--col-end",
        type=int,
        default=5,
        help="结束列 (0-based, 默认: 5)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存图片",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=BACKEND_URL,
        help=f"后端地址 (默认: {BACKEND_URL})",
    )

    args = parser.parse_args()

    # 更新全局变量
    global BACKEND_URL
    BACKEND_URL = args.url

    test_sheet_image(
        file_path=args.file_path,
        sheet_name=args.sheet,
        row_start=args.row_start,
        row_end=args.row_end,
        col_start=args.col_start,
        col_end=args.col_end,
        save_image=not args.no_save,
    )


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("用法: python test_sheet_image.py <文件路径> [选项]")
        print("\n示例:")
        print("  python test_sheet_image.py /path/to/test.xlsx")
        print("  python test_sheet_image.py /path/to/test.xlsx --sheet Sheet1 --row-start 0 --row-end 50")
        print("  python test_sheet_image.py /path/to/test.csv --sheet __default__")
        print("\n选项:")
        print("  --sheet NAME        Sheet 名称")
        print("  --row-start N       起始行 (0-based)")
        print("  --row-end N         结束行 (0-based)")
        print("  --col-start N       起始列 (0-based)")
        print("  --col-end N         结束列 (0-based)")
        print("  --no-save           不保存图片")
        print("  --url URL           后端地址")
        sys.exit(1)

    main()

