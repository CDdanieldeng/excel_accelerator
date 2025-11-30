"""Chat with Data API router."""

import logging
import uuid
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.models.schemas import (
    ChatInitRequest,
    ChatInitResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    FinalAnswer,
    TableSchema,
)
from backend.services.table_metadata_service import get_metadata_service
from backend.services.chat_flow import create_chat_flow, ChatState
from backend.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory session storage: session_id -> ChatState
_sessions: Dict[str, Dict[str, Any]] = {}


@router.post("/init", response_model=ChatInitResponse)
async def init_chat(request: Request, req: ChatInitRequest) -> ChatInitResponse:
    """
    Initialize a chat session.

    Args:
        request: FastAPI request object
        req: Chat initialization request

    Returns:
        ChatInitResponse with session_id and table_schema
    """
    request_logger = get_logger(__name__)
    request_logger.info(f"Chat init request: table_id={req.table_id}")

    # Get table schema
    metadata_service = get_metadata_service()
    table_schema = metadata_service.get_table_schema(req.table_id)

    if table_schema is None:
        request_logger.warning(f"Table not found: table_id={req.table_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "code": "TABLE_NOT_FOUND",
                "message": f"表 {req.table_id} 不存在，请先构建DataFrame",
            },
        )

    # Generate session ID
    session_id = str(uuid.uuid4())

    # Store session info
    _sessions[session_id] = {
        "table_id": req.table_id,
        "user_id": req.user_id,
    }

    request_logger.info(f"Chat session created: session_id={session_id}, table_id={req.table_id}")

    return ChatInitResponse(
        session_id=session_id,
        table_schema=table_schema,
    )


@router.post("/message", response_model=ChatMessageResponse)
async def chat_message(request: Request, req: ChatMessageRequest) -> ChatMessageResponse:
    """
    Process a chat message.

    Args:
        request: FastAPI request object
        req: Chat message request

    Returns:
        ChatMessageResponse with final answer, thinking summary, and debug info
    """
    request_logger = get_logger(__name__)
    request_logger.info(f"Chat message: session_id={req.session_id}, query='{req.user_query}'")

    # Check session
    session_info = _sessions.get(req.session_id)
    if not session_info:
        request_logger.warning(f"Session not found: session_id={req.session_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": "会话不存在，请先初始化聊天",
            },
        )

    table_id = session_info["table_id"]

    # Get table schema
    metadata_service = get_metadata_service()
    table_schema = metadata_service.get_table_schema(table_id)
    if not table_schema:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "TABLE_NOT_FOUND",
                "message": f"表 {table_id} 不存在",
            },
        )

    # Create initial state
    initial_state: ChatState = {
        "session_id": req.session_id,
        "table_id": table_id,
        "table_schema": table_schema,
        "user_query": req.user_query,
        "intent": None,
        "plan": None,
        "bound_plan": None,
        "pandas_code": None,
        "short_explanation": None,
        "execution_result": None,
        "thinking_steps": [],
        "final_answer": None,
        "error": None,
    }

    # Run the flow
    try:
        flow = create_chat_flow()
        final_state = flow.invoke(initial_state)

        # Check for errors
        if final_state.get("error"):
            error_msg = final_state["error"]
            request_logger.error(f"Flow error: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "FLOW_ERROR",
                    "message": error_msg,
                },
            )

        # Build response
        final_answer_text = final_state.get("final_answer", "无法生成回答")
        pandas_code = final_state.get("pandas_code", "")
        thinking_steps = final_state.get("thinking_steps", [])

        # If no thinking steps, add a default one
        if not thinking_steps:
            thinking_steps = ["执行数据分析"]

        response = ChatMessageResponse(
            final_answer=FinalAnswer(
                text=final_answer_text,
                pandas_code=pandas_code,
            ),
            thinking_summary=thinking_steps,
            debug={
                "plan_raw": final_state.get("plan"),
                "bound_plan": final_state.get("bound_plan"),
                "short_explanation": final_state.get("short_explanation"),
            },
        )

        request_logger.info(f"Chat message processed successfully: session_id={req.session_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        request_logger.exception(f"Unexpected error in chat message: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": f"处理消息时发生错误: {str(e)}",
            },
        )

