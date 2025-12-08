"""Streamlit frontend for Excel/CSV table header detection and DataFrame building."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st

from frontend.utils import init_session_state
from frontend.components import upload_page, header_select_page, preview_page
from frontend.pages import chat_page

# Page config
st.set_page_config(
    page_title="Excel Accelerator",
    page_icon="📊",
    layout="wide",
)


def main() -> None:
    """Main Streamlit application."""
    init_session_state()

    # Page routing
    page = st.session_state.page

    if page == "upload":
        upload_page.render()
    elif page == "header_select":
        header_select_page.render()
    elif page == "preview":
        preview_page.render()
    elif page == "chat":
        chat_page.render()
    else:
        st.error(f"Unknown page: {page}")
        st.session_state.page = "upload"
        st.rerun()


if __name__ == "__main__":
    main()
