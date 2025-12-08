"""FastAPI main application for Chatbot service."""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend import config
from backend.logging_config import request_id_context, setup_logging, get_logger
from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.llm_service import LLMService

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Initialize LLM service
llm_service = LLMService(
    provider=config.LLM_PROVIDER,
    provider_config={
        "api_key": config.LLM_API_KEY,
        "model": config.LLM_MODEL if config.LLM_MODEL else None,
        "base_url": config.LLM_BASE_URL,
    },
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup/shutdown."""
    logger.info("Starting Chatbot service...")
    yield
    logger.info("Shutting down Chatbot service...")


app = FastAPI(
    title="Chatbot API",
    description="API for chatbot functionality",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request_id to request state and logging context."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Set request_id in context variable for this request
    token = request_id_context.set(request_id)

    try:
        response = await call_next(request)
    finally:
        # Reset context variable
        request_id_context.reset(token)

    return response


def get_request_logger(request: Request) -> logging.Logger:
    """Get logger with request_id from context."""
    return logger


@app.post("/api/chat", response_model=ChatResponse)
async def chat_api(
    request: Request,
    chat_request: ChatRequest,
) -> ChatResponse:
    """
    Chatbot API endpoint.

    Args:
        request: FastAPI request object
        chat_request: Chat request with user message and optional dataset_id

    Returns:
        ChatResponse with chatbot response

    Raises:
        HTTPException: If processing fails
    """
    request_logger = get_request_logger(request)

    try:
        request_logger.info(
            f"Chat request: message_length={len(chat_request.message)}, "
            f"dataset_id={chat_request.dataset_id}, provider={config.LLM_PROVIDER}",
            extra={"stage": "chat", "dataset_id": chat_request.dataset_id},
        )

        # Generate response using LLM service
        response_text = llm_service.generate_response(
            message=chat_request.message,
            dataset_id=chat_request.dataset_id,
        )

        request_logger.info(
            f"Chat response generated: response_length={len(response_text)}, provider={config.LLM_PROVIDER}",
            extra={"stage": "complete", "dataset_id": chat_request.dataset_id},
        )

        return ChatResponse(response=response_text)

    except Exception as e:
        request_logger.exception(
            f"Unexpected error in chat API: {str(e)}",
            extra={"stage": "error", "dataset_id": chat_request.dataset_id},
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "处理聊天请求时发生错误，请稍后重试。",
            },
        )


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "chatbot"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.chatbot_main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level=config.LOG_LEVEL.lower(),
    )
