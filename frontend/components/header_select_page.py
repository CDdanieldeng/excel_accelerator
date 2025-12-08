"""Header selection page with sheet image preview."""

import base64
import io
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
from PIL import Image

from frontend.utils import call_sheet_list_api, call_sheet_image_api, call_build_dataframe_api


def render():
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

