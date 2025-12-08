"""Upload page for file selection."""

import streamlit as st


def render():
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

