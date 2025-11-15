"""Streamlit frontend for Excel/CSV table header detection."""

import base64
import io
import requests
import streamlit as st
from PIL import Image
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


def call_sheet_list_api(
    file_content: bytes,
    file_name: str,
) -> Optional[dict]:
    """
    Call backend API to get sheet list from uploaded file.

    Args:
        file_content: File content as bytes
        file_name: File name

    Returns:
        Response JSON or None if error
    """
    try:
        files = {"file": (file_name, file_content)}

        response = requests.post(
            f"{BACKEND_URL}/api/sheet_list",
            files=files,
            timeout=30,
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
        st.error("**超时错误**: 请求超时，请稍后重试。")
        return None
    except Exception as e:
        st.error(f"**请求错误**: {str(e)}")
        return None


def call_sheet_image_api(
    file_content: bytes,
    file_name: str,
    sheet_name: str,
    row_start: int,
    row_end: int,
    col_start: int,
    col_end: int,
) -> Optional[dict]:
    """
    Call backend API to render sheet region as PNG image.

    Args:
        file_content: File content as bytes
        file_name: File name
        sheet_name: Sheet name
        row_start: Start row index
        row_end: End row index
        col_start: Start column index
        col_end: End column index

    Returns:
        Response JSON or None if error
    """
    try:
        files = {"file": (file_name, file_content)}
        params = {
            "sheet_name": sheet_name,
            "row_start": row_start,
            "row_end": row_end,
            "col_start": col_start,
            "col_end": col_end,
        }

        response = requests.post(
            f"{BACKEND_URL}/api/sheet_image",
            files=files,
            params=params,
            timeout=60,
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
        st.error("**超时错误**: 请求超时，请稍后重试。")
        return None
    except Exception as e:
        st.error(f"**请求错误**: {str(e)}")
        return None


def main() -> None:
    """Main Streamlit application."""
    # Page navigation
    page = st.sidebar.selectbox(
        "选择功能",
        ["表头自动猜测", "Sheet 图片渲染"],
    )

    if page == "表头自动猜测":
        render_header_detection_page()
    else:
        render_sheet_image_page()


def render_header_detection_page() -> None:
    """Render the header detection page."""
    st.title("📊 Excel/CSV 表头自动猜测工具")
    
    # Show warning that this feature is temporarily disabled
    st.warning("⚠️ **功能暂时禁用**: 表头自动猜测功能正在调试中，暂时不可用。请使用 'Sheet 图片渲染' 功能。")
    
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

        # Analyze button (disabled)
        if st.button("🚀 开始分析", type="primary", use_container_width=True, disabled=True):
            st.info("此功能暂时不可用，请使用 'Sheet 图片渲染' 功能。")
        
        # Show info about disabled feature
        st.info("💡 **提示**: 表头自动猜测功能正在调试中。如需查看文件内容，请切换到 'Sheet 图片渲染' 页面。")

    else:
        st.info("👆 请上传一个文件开始分析")


def render_sheet_image_page() -> None:
    """Render the sheet image page."""
    st.title("🖼️ Sheet 图片渲染")
    st.markdown(
        "上传 Excel 或 CSV 文件，将指定 sheet 区域渲染为 PNG 图片。"
        "支持格式: `.xlsx`, `.csv`"
    )

    # File uploader
    uploaded_file = st.file_uploader(
        "上传 Excel/CSV 文件",
        type=["xlsx", "csv"],
        help="选择要渲染的文件",
    )

    if uploaded_file is not None:
        # Display file info
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        st.info(f"📄 **文件名**: {uploaded_file.name} | **大小**: {file_size_mb:.2f} MB")

        # Get sheet list
        file_content = uploaded_file.getvalue()
        sheet_list_result = call_sheet_list_api(file_content, uploaded_file.name)

        if sheet_list_result is None:
            st.error("❌ 无法获取 Sheet 列表，请检查文件格式是否正确")
            return

        sheet_names = sheet_list_result.get("sheets", [])
        if not sheet_names:
            st.warning("⚠️ 文件中没有找到任何 Sheet")
            return

        # Input form
        with st.form("sheet_image_form"):
            st.subheader("📝 输入参数")

            col1, col2 = st.columns(2)

            with col1:
                # Use dropdown for sheet selection
                default_sheet = sheet_names[0] if sheet_names else "__default__"
                sheet_name = st.selectbox(
                    "Sheet 名称",
                    options=sheet_names,
                    index=0,
                    help="选择要渲染的 Sheet",
                )

            with col2:
                st.markdown("")  # Spacer for alignment

            st.subheader("📐 行列范围")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                row_start = st.number_input(
                    "起始行 (0-based)",
                    min_value=0,
                    value=0,
                    step=1,
                    help="0-based 起始行索引（包含）",
                )

            with col2:
                row_end = st.number_input(
                    "结束行 (0-based)",
                    min_value=0,
                    value=50,
                    step=1,
                    help="0-based 结束行索引（包含）",
                )

            with col3:
                col_start = st.number_input(
                    "起始列 (0-based)",
                    min_value=0,
                    value=0,
                    step=1,
                    help="0-based 起始列索引（包含）",
                )

            with col4:
                col_end = st.number_input(
                    "结束列 (0-based)",
                    min_value=0,
                    value=10,
                    step=1,
                    help="0-based 结束列索引（包含）",
                )

            submit_button = st.form_submit_button("🚀 渲染图片", type="primary", use_container_width=True)

        if submit_button:
            # Validate ranges
            if row_end < row_start:
                st.error("❌ 结束行必须 >= 起始行")
                return

            if col_end < col_start:
                st.error("❌ 结束列必须 >= 起始列")
                return

            with st.spinner("正在渲染图片，请稍候..."):
                # Read file content
                file_content = uploaded_file.getvalue()

                result = call_sheet_image_api(
                    file_content=file_content,
                    file_name=uploaded_file.name,
                    sheet_name=sheet_name,
                    row_start=int(row_start),
                    row_end=int(row_end),
                    col_start=int(col_start),
                    col_end=int(col_end),
                )

            if result:
                st.success("✅ 图片渲染完成！")

                # Decode base64 image
                try:
                    image_base64 = result["image_base64"]
                    image_bytes = base64.b64decode(image_base64)
                    image = Image.open(io.BytesIO(image_bytes))

                    # Display image
                    st.subheader("🖼️ 渲染结果")
                    st.image(image, use_container_width=True)

                    # Display metadata
                    st.subheader("📊 元信息")
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Sheet 名称**: `{result['sheet_name']}`")
                        st.markdown(
                            f"**行范围**: [{result['row_start']}, {result['row_end']}] "
                            f"（用户视角: 第 {result['row_start'] + 1} 行到第 {result['row_end'] + 1} 行）"
                        )
                        st.markdown(
                            f"**列范围**: [{result['col_start']}, {result['col_end']}] "
                            f"（用户视角: 第 {result['col_start'] + 1} 列到第 {result['col_end'] + 1} 列）"
                        )

                    with col2:
                        st.markdown(f"**行高**: {result['row_height_px']} 像素")
                        st.markdown(f"**列宽**: {result['col_width_px']} 像素")
                        st.markdown(f"**图片大小**: {image.width} x {image.height} 像素")

                except Exception as e:
                    st.error(f"❌ 解析图片时出错: {str(e)}")


if __name__ == "__main__":
    main()

