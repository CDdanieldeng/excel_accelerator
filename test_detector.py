#!/usr/bin/env python3
"""直接测试表头检测功能的脚本，不依赖 API。"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.services.file_loader import load_file_sample
from backend.services.table_detector import TableDetector


def detect_table_headers(file_path: str, max_scan_rows: int = 200, max_preview_rows: int = 50):
    """
    直接检测文件中的表头。

    Args:
        file_path: 文件路径
        max_scan_rows: 最大扫描行数
        max_preview_rows: 最大预览行数
    """
    print("=" * 80)
    print("表头检测测试")
    print("=" * 80)
    print(f"文件: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ 错误: 文件不存在: {file_path}")
        return

    # 检测文件类型
    file_ext = Path(file_path).suffix.lower().lstrip('.')
    if file_ext not in ['xlsx', 'csv', 'xlsb']:
        print(f"❌ 错误: 不支持的文件类型: {file_ext}")
        print("   支持的类型: xlsx, csv, xlsb")
        return

    print(f"文件类型: {file_ext}")
    print(f"最大扫描行数: {max_scan_rows}")
    print(f"最大预览行数: {max_preview_rows}")
    print("-" * 80)

    try:
        # 加载文件样本
        print("\n📂 正在加载文件...")
        samples = load_file_sample(file_path, file_ext, max_scan_rows)
        print(f"✅ 加载完成，共 {len(samples)} 个 sheet\n")

        # 检测表头
        detector = TableDetector()
        results = []

        for sample in samples:
            print(f"🔍 正在检测 Sheet: {sample.name}")
            print(f"   总行数: {len(sample.rows)}")
            
            result = detector.detect_sheet(
                sample.name,
                sample.rows,
                max_preview_rows=max_preview_rows
            )
            results.append(result)

            print(f"   ✅ 检测完成")
            print()

        # 标记主表
        results = detector.mark_main_sheet(results, samples)

        # 显示结果
        print("=" * 80)
        print("检测结果")
        print("=" * 80)

        for i, result in enumerate(results, 1):
            print(f"\n📊 Sheet {i}: {result.name}")
            if result.is_main:
                print("   🎯 主表")
            
            # Display header row information
            if len(result.header_row_indices) == 1:
                print(f"   表头行: 第 {result.header_row_index + 1} 行 (0-based 索引: {result.header_row_index})")
            else:
                header_rows_display = ", ".join([f"第 {idx + 1} 行" for idx in result.header_row_indices])
                print(f"   表头行: {header_rows_display} (多行表头, 0-based 索引: {result.header_row_indices})")
                print(f"   表头起始行: 第 {result.header_row_index + 1} 行 (0-based 索引: {result.header_row_index})")
            
            print(f"   数据起始行: 第 {result.data_start_row_index + 1} 行 (0-based 索引: {result.data_start_row_index})")
            print(f"   检测到的列数: {len(result.detected_columns)}")
            
            if result.detected_columns:
                print(f"\n   列名列表:")
                for j, col in enumerate(result.detected_columns, 1):
                    col_display = col if col else "(空)"
                    print(f"     {j:3d}. {col_display}")
            else:
                print("   ⚠️  未检测到列名")

            # 显示预览数据
            if result.preview.rows:
                num_header_rows = len(result.header_row_indices)
                num_data_rows = len(result.preview.rows) - num_header_rows
                
                print(f"\n   数据预览 (表头 {num_header_rows} 行 + 数据 {num_data_rows} 行):")
                print("   " + "-" * 76)
                
                # 显示表头行（可能有多行）
                for header_idx, header_row in enumerate(result.preview.rows[:num_header_rows]):
                    header_label = f"[表头{header_idx + 1}]" if num_header_rows > 1 else "[表头]"
                    header_str = " | ".join([str(cell)[:15] if cell else "(空)" for cell in header_row[:5]])
                    if len(header_row) > 5:
                        header_str += f" ... (共 {len(header_row)} 列)"
                    print(f"   {header_label} {header_str}")
                
                print("   " + "-" * 76)
                
                # 显示数据行（最多 5 行）
                data_start_idx = num_header_rows
                for row_idx, row in enumerate(result.preview.rows[data_start_idx:data_start_idx + 5], 1):
                    row_str = " | ".join([str(cell)[:15] if cell else "(空)" for cell in row[:5]])
                    if len(row) > 5:
                        row_str += f" ... (共 {len(row)} 列)"
                    print(f"   [{row_idx:2d}]  {row_str}")
                
                if len(result.preview.rows) > data_start_idx + 5:
                    print(f"   ... (还有 {len(result.preview.rows) - data_start_idx - 5} 行)")
            else:
                print("   📭 无预览数据")

            print()

        print("=" * 80)
        print("✅ 检测完成")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数。"""
    if len(sys.argv) < 2:
        print("用法: python test_detector.py <文件路径> [max_scan_rows] [max_preview_rows]")
        print("\n示例:")
        print("  python test_detector.py test.xlsx")
        print("  python test_detector.py data.csv 500 100")
        print("\n参数说明:")
        print("  <文件路径>        : 要检测的文件路径 (必需)")
        print("  max_scan_rows     : 最大扫描行数 (可选，默认 200)")
        print("  max_preview_rows  : 最大预览行数 (可选，默认 50)")
        sys.exit(1)

    file_path = sys.argv[1]
    max_scan_rows = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    max_preview_rows = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    detect_table_headers(file_path, max_scan_rows, max_preview_rows)


if __name__ == "__main__":
    main()

