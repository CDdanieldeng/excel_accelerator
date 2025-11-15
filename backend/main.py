"""FastAPI main application for Excel/CSV table header detection."""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Tuple

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend import config
from backend.logging_config import request_id_context, setup_logging, get_logger
from backend.models.schemas import ErrorDetail, ErrorResponse, GuessTableResponse
from backend.services.file_loader import load_file_sample
from backend.services.table_detector import TableDetector
from backend.utils.io_utils import cleanup_temp_file, get_file_size_mb, save_uploaded_file

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup/shutdown."""
    logger.info("Starting Excel Accelerator backend...")
    yield
    logger.info("Shutting down Excel Accelerator backend...")


app = FastAPI(
    title="Excel/CSV Table Header Detection API",
    description="API for automatically detecting table headers and data regions in Excel/CSV files",
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


def detect_file_type(file_name: str) -> str:
    """
    Detect file type from file name extension.

    Args:
        file_name: File name

    Returns:
        File type (xlsx, csv, xlsb)

    Raises:
        ValueError: If file type is not supported
    """
    ext = file_name.lower().split(".")[-1] if "." in file_name else ""
    if ext not in config.ALLOWED_FILE_TYPES:
        raise ValueError(f"Unsupported file type: {ext}")
    return ext


def validate_uploaded_file(
    file: UploadFile,
    file_content: bytes,
    request_logger: logging.Logger,
) -> Tuple[str, str]:
    """
    Validate uploaded file (size, type, encryption).

    Args:
        file: Uploaded file object
        file_content: File content as bytes
        request_logger: Logger instance (request_id from context)

    Returns:
        Tuple of (file_type, temp_file_path)

    Raises:
        HTTPException: If validation fails
    """
    file_name = file.filename or "unknown"
    file_size = len(file_content)
    file_size_mb = file_size / (1024 * 1024)

    request_logger.info(
        f"Validating file: name={file_name}, size={file_size_mb:.2f}MB, "
        f"mime_type={file.content_type}",
        extra={"stage": "validate"},
    )

    # Check file size
    if file_size > config.MAX_FILE_SIZE_BYTES:
        request_logger.warning(
            f"File too large: {file_name}, size={file_size_mb:.2f}MB, "
            f"limit={config.MAX_FILE_SIZE_MB}MB",
            extra={"stage": "validate"},
        )
        raise HTTPException(
            status_code=413,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"文件超过大小限制（最大 {config.MAX_FILE_SIZE_MB}MB），请拆分或压缩后再上传。",
                "max_file_size_mb": config.MAX_FILE_SIZE_MB,
            },
        )

    # Check file type
    try:
        file_type = detect_file_type(file_name)
    except ValueError as e:
        request_logger.warning(
            f"Unsupported file type: {file_name}, error={str(e)}",
            extra={"stage": "validate"},
        )
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"不支持的文件类型。仅支持: {', '.join(config.ALLOWED_FILE_TYPES)}",
            },
        )

    # Save to temporary file
    try:
        temp_file_path = save_uploaded_file(file_content, file_name)
    except Exception as e:
        request_logger.exception(
            f"Error saving uploaded file: {file_name}",
            extra={"stage": "validate"},
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "保存上传文件时发生错误，请稍后重试。",
            },
        )

    # Check for encryption (for xlsx and xlsb)
    if file_type in ("xlsx", "xlsb"):
        try:
            if file_type == "xlsx":
                from openpyxl import load_workbook

                workbook = load_workbook(temp_file_path, read_only=True)
                workbook.close()
            elif file_type == "xlsb":
                try:
                    import pyxlsb

                    with pyxlsb.open_workbook(temp_file_path) as wb:
                        pass  # Just try to open
                except ImportError:
                    request_logger.warning("pyxlsb not available, skipping encryption check")
        except Exception as e:
            error_msg = str(e).lower()
            if "encrypted" in error_msg or "password" in error_msg or "protected" in error_msg:
                cleanup_temp_file(temp_file_path)
                request_logger.error(
                    f"Encrypted/protected file detected: {file_name}, error={str(e)}",
                    extra={"stage": "validate"},
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "FILE_ENCRYPTED",
                        "message": "检测到文件可能被加密或受密码保护，请解除密码后再上传。",
                    },
                )
            else:
                # Other errors during encryption check - log but don't fail
                request_logger.warning(
                    f"Error during encryption check (non-fatal): {file_name}, error={str(e)}",
                    extra={"stage": "validate"},
                )

    request_logger.info(
        f"File validation passed: {file_name}, type={file_type}",
        extra={"stage": "validate"},
    )

    return file_type, temp_file_path


@app.post("/api/guess_table", response_model=GuessTableResponse)
async def guess_table(
    request: Request,
    file: UploadFile = File(...),
    max_preview_rows: int = 50,
    max_scan_rows: int = 200,
) -> GuessTableResponse:
    """
    Analyze uploaded file and detect table headers and data regions.

    Args:
        request: FastAPI request object
        file: Uploaded file
        max_preview_rows: Maximum number of preview rows to return
        max_scan_rows: Maximum number of rows to scan for detection

    Returns:
        GuessTableResponse with detection results

    Raises:
        HTTPException: If file processing fails
    """
    request_logger = get_request_logger(request)
    request_id = request.state.request_id
    temp_file_path: Optional[str] = None

    try:
        # Read file content
        file_content = await file.read()
        file_name = file.filename or "unknown"

        request_logger.info(
            f"Received file upload: {file_name}, size={len(file_content)} bytes",
            extra={"stage": "upload", "file_name": file_name},
        )

        # Validate file
        file_type, temp_file_path = validate_uploaded_file(file, file_content, request_logger)

        # Load file sample
        request_logger.info(
            f"Loading file sample: {file_name}, type={file_type}, max_scan_rows={max_scan_rows}",
            extra={"stage": "load_sample", "file_name": file_name},
        )

        try:
            samples = load_file_sample(temp_file_path, file_type, max_scan_rows)
            request_logger.info(
                f"Loaded {len(samples)} sheet(s) from file: {file_name}",
                extra={"stage": "load_sample", "file_name": file_name},
            )
        except Exception as e:
            request_logger.exception(
                f"Error loading file sample: {file_name}",
                extra={"stage": "load_sample", "file_name": file_name},
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "INTERNAL_ERROR",
                    "message": "解析文件时发生错误，请稍后重试或联系管理员。",
                },
            )

        # Detect tables
        detector = TableDetector()
        results = []

        for sample in samples:
            request_logger.info(
                f"Detecting table in sheet: {sample.name}, rows={len(sample.rows)}",
                extra={"stage": "detect_header", "file_name": file_name, "sheet_name": sample.name},
            )

            try:
                result = detector.detect_sheet(
                    sample.name,
                    sample.rows,
                    max_preview_rows=max_preview_rows,
                )
                results.append(result)

                request_logger.info(
                    f"Sheet {sample.name}: header_row={result.header_row_index}, "
                    f"data_start={result.data_start_row_index}, "
                    f"columns={len(result.detected_columns)}",
                    extra={
                        "stage": "detect_header",
                        "file_name": file_name,
                        "sheet_name": sample.name,
                    },
                )
            except Exception as e:
                request_logger.exception(
                    f"Error detecting table in sheet: {sample.name}",
                    extra={
                        "stage": "detect_header",
                        "file_name": file_name,
                        "sheet_name": sample.name,
                    },
                )
                raise HTTPException(
                    status_code=500,
                    detail={
                        "code": "INTERNAL_ERROR",
                        "message": f"检测表头时发生错误（sheet: {sample.name}），请稍后重试。",
                    },
                )

        # Mark main sheet
        results = detector.mark_main_sheet(results, samples)

        # Build response
        response = GuessTableResponse(
            file_name=file_name,
            file_type=file_type,
            sheets=results,
        )

        request_logger.info(
            f"Successfully processed file: {file_name}, sheets={len(results)}",
            extra={"stage": "complete", "file_name": file_name},
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        request_logger.exception(
            f"Unexpected error processing file: {file.filename}",
            extra={"stage": "error", "file_name": file.filename or "unknown"},
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "处理文件时发生未预期的错误，请稍后重试或联系管理员。",
            },
        )
    finally:
        # Cleanup temporary file
        if temp_file_path:
            cleanup_temp_file(temp_file_path)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "excel-accelerator"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=config.LOG_LEVEL.lower(),
    )

