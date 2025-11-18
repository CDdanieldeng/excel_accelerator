"""Streamlit frontend for Excel/CSV table header detection and DataFrame building."""

import base64
import io
import requests
import streamlit as st
from PIL import Image
from typing import Optional
import pandas as pd

# Backend API URL
BACKEND_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="Excel Accelerator",
    page_icon="📊",
    layout="wide",
)


# Initialize session state
def init_session_state():
    """Initialize session state variables."""
    if "page" not in st.session_state:
        st.session_state.page = "upload"
    if "file_content" not in st.session_state:
        st.session_state.file_content = None
    if "file_name" not in st.session_state:
        st.session_state.file_name = None
    if "sheet_name" not in st.session_state:
        st.session_state.sheet_name = None
    if "header_row_number" not in st.session_state:
        st.session_state.header_row_number = None
    if "current_dataset_id" not in st.session_state:
        st.session_state.current_dataset_id = None
    if "current_dataset_preview" not in st.session_state:
        st.session_state.current_dataset_preview = None
    if "current_dataset_schema" not in st.session_state:
        st.session_state.current_dataset_schema = None
    if "current_dataset_info" not in st.session_state:
        st.session_state.current_dataset_info = None


def call_sheet_list_api(
    file_content: bytes,
    file_name: str,
) -> Optional[dict]:
    """Call backend API to get sheet list from uploaded file."""
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

            st.error(f"**Error Code**: {error_code}\n\n**Error Message**: {error_message}")
            return None

    except requests.exceptions.ConnectionError:
        st.error(
            "**Connection Error**: Unable to connect to backend service. Please ensure the backend is running.\n\n"
            f"Backend URL: {BACKEND_URL}"
        )
        return None
    except requests.exceptions.Timeout:
        st.error("**Timeout Error**: Request timed out. Please try again later.")
        return None
    except Exception as e:
        st.error(f"**Request Error**: {str(e)}")
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
    """Call backend API to render sheet region as PNG image."""
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

            st.error(f"**Error Code**: {error_code}\n\n**Error Message**: {error_message}")
            return None

    except requests.exceptions.ConnectionError:
        st.error(
            "**Connection Error**: Unable to connect to backend service. Please ensure the backend is running.\n\n"
            f"Backend URL: {BACKEND_URL}"
        )
        return None
    except requests.exceptions.Timeout:
        st.error("**Timeout Error**: Request timed out. Please try again later.")
        return None
    except Exception as e:
        st.error(f"**Request Error**: {str(e)}")
        return None


def call_build_dataframe_api(
    file_content: bytes,
    file_name: str,
    sheet_name: str,
    header_row_number: int,
    max_preview_rows: int = 100,
) -> Optional[dict]:
    """Call backend API to build DataFrame from header row."""
    try:
        files = {"file": (file_name, file_content)}
        params = {
            "sheet_name": sheet_name,
            "header_row_number": header_row_number,
            "max_preview_rows": max_preview_rows,
        }

        response = requests.post(
            f"{BACKEND_URL}/api/build_dataframe",
            files=files,
            params=params,
            timeout=120,
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

            st.error(f"**Error Code**: {error_code}\n\n**Error Message**: {error_message}")
            return None

    except requests.exceptions.ConnectionError:
        st.error(
            "**Connection Error**: Unable to connect to backend service. Please ensure the backend is running.\n\n"
            f"Backend URL: {BACKEND_URL}"
        )
        return None
    except requests.exceptions.Timeout:
        st.error("**Timeout Error**: Request timed out. Please try again later.")
        return None
    except Exception as e:
        st.error(f"**Request Error**: {str(e)}")
        return None


def render_upload_page():
    """Render file upload page."""
    st.title("📤 Upload File")
    st.markdown("Upload an Excel or CSV file to start analysis. Supported formats: `.xlsx`, `.csv`")

    uploaded_file = st.file_uploader(
        "Upload Excel/CSV File",
        type=["xlsx", "csv"],
        help="Select a file to analyze",
    )

    if uploaded_file is not None:
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        st.info(f"📄 **File Name**: {uploaded_file.name} | **Size**: {file_size_mb:.2f} MB")

        if st.button("✅ Confirm File", type="primary", use_container_width=True):
            # Save file info to session state
            st.session_state.file_content = uploaded_file.getvalue()
            st.session_state.file_name = uploaded_file.name
            st.session_state.page = "header_select"
            st.rerun()


def render_header_select_page():
    """Render header selection page with sheet image preview."""
    st.title("📋 Select Header Row")
    st.markdown("View the sheet preview image to determine the header row number (1-based).")

    if st.session_state.file_content is None:
        st.warning("⚠️ File not found. Please return to the upload page.")
        if st.button("⬅️ Back to Upload"):
            st.session_state.page = "upload"
            st.rerun()
        return

    # Get sheet list
    sheet_list_result = call_sheet_list_api(st.session_state.file_content, st.session_state.file_name)

    if sheet_list_result is None:
        st.error("❌ Unable to get sheet list. Please check if the file format is correct.")
        return

    sheet_names = sheet_list_result.get("sheets", [])
    if not sheet_names:
        st.warning("⚠️ No sheets found in the file")
        return

    # Sheet selection
    default_sheet = sheet_names[0] if sheet_names else "__default__"
    if st.session_state.sheet_name is None:
        st.session_state.sheet_name = default_sheet

    sheet_name = st.selectbox(
        "Sheet Name",
        options=sheet_names,
        index=sheet_names.index(st.session_state.sheet_name) if st.session_state.sheet_name in sheet_names else 0,
        help="Select the sheet to analyze",
    )
    st.session_state.sheet_name = sheet_name

    # Image preview section
    st.subheader("🖼️ Sheet Preview")
    st.markdown("View the sheet preview image to find the header row number.")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        row_start = st.number_input(
            "Start Row (0-based)",
            min_value=0,
            value=0,
            step=1,
            help="0-based start row index (inclusive)",
        )

    with col2:
        row_end = st.number_input(
            "End Row (0-based)",
            min_value=0,
            value=50,
            step=1,
            help="0-based end row index (inclusive)",
        )

    with col3:
        col_start = st.number_input(
            "Start Column (0-based)",
            min_value=0,
            value=0,
            step=1,
            help="0-based start column index (inclusive)",
        )

    with col4:
        col_end = st.number_input(
            "End Column (0-based)",
            min_value=0,
            value=10,
            step=1,
            help="0-based end column index (inclusive)",
        )

    if st.button("🖼️ Render Preview", use_container_width=True):
        if row_end < row_start or col_end < col_start:
            st.error("❌ Invalid range: end value must be >= start value")
        else:
            with st.spinner("Rendering image, please wait..."):
                result = call_sheet_image_api(
                    file_content=st.session_state.file_content,
                    file_name=st.session_state.file_name,
                    sheet_name=sheet_name,
                    row_start=int(row_start),
                    row_end=int(row_end),
                    col_start=int(col_start),
                    col_end=int(col_end),
                )

            if result:
                try:
                    image_base64 = result["image_base64"]
                    image_bytes = base64.b64decode(image_base64)
                    image = Image.open(io.BytesIO(image_bytes))
                    st.image(image, use_container_width=True)
                except Exception as e:
                    st.error(f"❌ Error parsing image: {str(e)}")

    st.divider()

    # Header row selection
    st.subheader("📝 Confirm Header Row")
    st.markdown("Enter the header row number (**1-based**, e.g., enter `1` for row 1, enter `12` for row 12).")

    header_row_number = st.number_input(
        "Header Row Number (1-based)",
        min_value=1,
        value=st.session_state.header_row_number if st.session_state.header_row_number else 1,
        step=1,
        help="Header row number (counting from 1)",
    )

    if st.button("✅ Confirm Header", type="primary", use_container_width=True):
        st.session_state.header_row_number = header_row_number

        with st.spinner("Building DataFrame, please wait..."):
            result = call_build_dataframe_api(
                file_content=st.session_state.file_content,
                file_name=st.session_state.file_name,
                sheet_name=sheet_name,
                header_row_number=header_row_number,
                max_preview_rows=100,
            )

        if result:
            # Save to session state
            st.session_state.current_dataset_id = result["dataset_id"]
            st.session_state.current_dataset_preview = result["preview_rows"]
            st.session_state.current_dataset_schema = result["columns"]
            st.session_state.current_dataset_info = {
                "file_name": result["file_name"],
                "sheet_name": result["sheet_name"],
                "header_row_number": result["header_row_number"],
                "n_rows": result["n_rows"],
                "n_cols": result["n_cols"],
            }

            # Switch to preview page
            st.session_state.page = "preview"
            st.rerun()

    # Back button
    if st.button("⬅️ Back to Upload"):
        st.session_state.page = "upload"
        st.rerun()


def render_preview_page():
    """Render DataFrame preview page."""
    st.title("📊 Data Preview")

    if st.session_state.current_dataset_info is None:
        st.warning("⚠️ Dataset information not found. Please return to header selection.")
        if st.button("⬅️ Back to Header Selection"):
            st.session_state.page = "header_select"
            st.rerun()
        return

    info = st.session_state.current_dataset_info

    # Display dataset info
    st.subheader("📋 Dataset Information")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**File Name**: `{info['file_name']}`")
        st.markdown(f"**Sheet Name**: `{info['sheet_name']}`")
        st.markdown(f"**Header Row**: Row {info['header_row_number']}")

    with col2:
        st.markdown(f"**Rows**: {info['n_rows']:,}")
        st.markdown(f"**Columns**: {info['n_cols']}")
        st.markdown(f"**Dataset ID**: `{st.session_state.current_dataset_id}`")

    st.divider()

    # Display DataFrame preview
    st.subheader("📈 Data Preview")
    if st.session_state.current_dataset_preview and st.session_state.current_dataset_schema:
        try:
            df = pd.DataFrame(
                st.session_state.current_dataset_preview,
                columns=st.session_state.current_dataset_schema,
            )
            st.dataframe(df, use_container_width=True, height=400)
        except Exception as e:
            st.error(f"❌ Error building DataFrame: {str(e)}")
    else:
        st.warning("⚠️ No preview data available")

    st.divider()

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💬 Start Chat with Data", type="primary", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()

    with col2:
        if st.button("⬅️ Back to Header Selection", use_container_width=True):
            st.session_state.page = "header_select"
            st.rerun()


def render_chat_page():
    """Render Chat with Data page (placeholder)."""
    st.title("💬 Chat with Data")

    if st.session_state.current_dataset_info is None:
        st.warning("⚠️ Dataset information not found. Please return to data preview.")
        if st.button("⬅️ Back to Data Preview"):
            st.session_state.page = "preview"
            st.rerun()
        return

    info = st.session_state.current_dataset_info

    # Display dataset info
    st.subheader("📋 Current Dataset")
    st.info(
        f"**File Name**: `{info['file_name']}` | "
        f"**Sheet**: `{info['sheet_name']}` | "
        f"**Header Row**: Row {info['header_row_number']} | "
        f"**Data Size**: {info['n_rows']:,} rows × {info['n_cols']} columns"
    )

    st.markdown(f"**Dataset ID**: `{st.session_state.current_dataset_id}`")

    st.divider()

    # Placeholder content
    st.subheader("🚧 Feature Placeholder")
    st.markdown(
        "This will integrate with LLM's Chat with Data functionality.\n\n"
        f"Using dataset_id: `{st.session_state.current_dataset_id}` for queries and analysis."
    )

    st.info(
        "💡 **Tip**: In the future, you can integrate LLM API here to enable natural language queries and analysis on the dataset."
    )

    st.divider()

    # Back button
    if st.button("⬅️ Back to Data Preview", use_container_width=True):
        st.session_state.page = "preview"
        st.rerun()


def main() -> None:
    """Main Streamlit application."""
    init_session_state()

    # Page routing
    page = st.session_state.page

    if page == "upload":
        render_upload_page()
    elif page == "header_select":
        render_header_select_page()
    elif page == "preview":
        render_preview_page()
    elif page == "chat":
        render_chat_page()
    else:
        st.error(f"Unknown page: {page}")
        st.session_state.page = "upload"
        st.rerun()


if __name__ == "__main__":
    main()
