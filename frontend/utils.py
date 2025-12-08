"""Shared utilities for the frontend application."""

import requests
import streamlit as st
from typing import Optional

# Backend API URL
BACKEND_URL = "http://localhost:8000"


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
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = None
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


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


def call_chat_init_api(table_id: str) -> Optional[dict]:
    """Call backend API to initialize chat session."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat/init",
            json={"table_id": table_id},
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


def call_chat_message_api(session_id: str, user_query: str, table_id: Optional[str] = None) -> Optional[dict]:
    """Call backend API to send chat message.
    
    Args:
        session_id: Chat session identifier
        user_query: User query text
        table_id: Optional table_id for session recovery if session is lost
    """
    try:
        payload = {"session_id": session_id, "user_query": user_query}
        if table_id:
            payload["table_id"] = table_id
        
        response = requests.post(
            f"{BACKEND_URL}/chat/message",
            json=payload,
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

