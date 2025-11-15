"""Streamlit frontend for Excel/CSV table header detection."""

import requests
import streamlit as st
from typing import Optional

# Backend API URL
BACKEND_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="Excel/CSV 表头自动猜测工具",
    page_icon="📊",
    layout="wide",
)


def call_backend_api(
    file_content: bytes,
    file_name: str,
    max_preview_rows: int = 50,
    max_scan_rows: int = 200,
) -> Optional[dict]:
    """
    Call backend API to analyze file.

    Args:
        file_content: File content as bytes
        file_name: File name
        max_preview_rows: Maximum preview rows
        max_scan_rows: Maximum scan rows

    Returns:
        Response JSON or None if error
    """
    try:
        files = {"file": (file_name, file_content)}
        params = {
            "max_preview_rows": max_preview_rows,
            "max_scan_rows": max_scan_rows,
        }

        response = requests.post(
            f"{BACKEND_URL}/api/guess_table",
            files=files,
            params=params,
            timeout=300,  # 5 minutes timeout
        )

        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json()
            error_detail = error_data.get("detail", {})
            if isinstance(error_detail, dict):
                error_code = error_detail.get("code", "UNKNOWN_ERROR")
                error_message = error_detail.get("message", "未知错误")
            else:
                error_code = "UNKNOWN_ERROR"
                error_message = str(error_detail)

            st.error(f"**错误代码**: {error_code}\n\n**错误信息**: {error_message}")
            return None

    except requests.exceptions.ConnectionError:
        st.error(
            "**连接错误**: 无法连接到后端服务。请确保后端服务正在运行。\n\n"
            f"后端地址: {BACKEND_URL}"
        )
        return None
    except requests.exceptions.Timeout:
        st.error("**超时错误**: 请求超时，文件可能过大或处理时间过长。")
        return None
    except Exception as e:
        st.error(f"**请求错误**: {str(e)}")
        return None


def display_sheet_result(sheet_result: dict) -> None:
    """
    Display detection result for a single sheet.

    Args:
        sheet_result: Sheet detection result dictionary
    """
    sheet_name = sheet_result["name"]
    is_main = sheet_result["is_main"]
    header_row_index = sheet_result["header_row_index"]
    data_start_row_index = sheet_result["data_start_row_index"]
    detected_columns = sheet_result["detected_columns"]
    preview_rows = sheet_result["preview"]["rows"]

    # Sheet header
    main_badge = " 🎯 **主表**" if is_main else ""
    st.subheader(f"📋 Sheet: `{sheet_name}`{main_badge}")

    col1, col2 = st.columns(2)

    with col1:
        # Display header row information (support multi-row headers)
        header_row_indices = sheet_result.get("header_row_indices", [header_row_index])
        if len(header_row_indices) == 1:
            st.markdown(f"**猜测表头行**: 第 {header_row_index + 1} 行（0-based 索引: {header_row_index}）")
        else:
            header_rows_display = "、".join([f"第 {idx + 1} 行" for idx in header_row_indices])
            st.markdown(f"**猜测表头行**: {header_rows_display}（多行表头）")
            st.markdown(f"**表头起始行**: 第 {header_row_index + 1} 行（0-based 索引: {header_row_index}）")
        
        st.markdown(
            f"**数据起始行**: 第 {data_start_row_index + 1} 行（0-based 索引: {data_start_row_index}）"
        )

    with col2:
        st.markdown(f"**检测到的列数**: {len(detected_columns)}")
        if len(header_row_indices) > 1:
            st.markdown(f"**表头行数**: {len(header_row_indices)} 行")

    # Display detected columns
    if detected_columns:
        st.markdown("**检测到的列名**:")
        columns_text = " | ".join([f"`{col}`" for col in detected_columns[:20]])
        if len(detected_columns) > 20:
            columns_text += f" ... (共 {len(detected_columns)} 列)"
        st.markdown(columns_text)
    else:
        st.warning("⚠️ 未检测到列名")

    # Display preview
    if preview_rows:
        st.markdown("**数据预览**:")
        # Convert to DataFrame for better display
        import pandas as pd

        # Use first row as column names if available
        if len(preview_rows) > 0:
            df = pd.DataFrame(preview_rows[1:], columns=preview_rows[0] if preview_rows else None)
            st.dataframe(df, use_container_width=True, height=400)
    else:
        st.info("📭 无预览数据")

    st.divider()


def main() -> None:
    """Main Streamlit application."""
    st.title("📊 Excel/CSV 表头自动猜测工具")
    st.markdown(
        "上传 Excel 或 CSV 文件，自动检测表头行和数据起始行。"
        "支持格式: `.xlsx`, `.csv`, `.xlsb`"
    )

    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ 配置")
        max_preview_rows = st.number_input(
            "预览行数",
            min_value=10,
            max_value=200,
            value=50,
            step=10,
            help="返回的数据预览行数",
        )
        max_scan_rows = st.number_input(
            "扫描行数",
            min_value=50,
            max_value=1000,
            value=200,
            step=50,
            help="用于检测表头的最大扫描行数",
        )
        st.divider()
        st.markdown("**后端地址**:")
        st.code(BACKEND_URL)

    # File uploader
    uploaded_file = st.file_uploader(
        "上传 Excel/CSV 文件",
        type=["xlsx", "csv", "xlsb"],
        help="选择要分析的文件",
    )

    if uploaded_file is not None:
        # Display file info
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        st.info(f"📄 **文件名**: {uploaded_file.name} | **大小**: {file_size_mb:.2f} MB")

        # Analyze button
        if st.button("🚀 开始分析", type="primary", use_container_width=True):
            with st.spinner("正在分析文件，请稍候..."):
                # Read file content
                file_content = uploaded_file.getvalue()

                # Call backend API
                result = call_backend_api(
                    file_content,
                    uploaded_file.name,
                    max_preview_rows=int(max_preview_rows),
                    max_scan_rows=int(max_scan_rows),
                )

                if result:
                    # Display file info
                    st.success("✅ 分析完成！")
                    st.markdown(f"**文件类型**: `{result['file_type']}`")
                    st.markdown(f"**Sheet 数量**: {len(result['sheets'])}")

                    # Display results for each sheet
                    for sheet_result in result["sheets"]:
                        display_sheet_result(sheet_result)

    else:
        st.info("👆 请上传一个文件开始分析")


if __name__ == "__main__":
    main()

