"""Data preview page."""

import streamlit as st
import pandas as pd


def render():
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

