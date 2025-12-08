"""Pydantic schemas for request/response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    max_file_size_mb: Optional[int] = Field(None, description="Max file size in MB (if applicable)")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: ErrorDetail = Field(..., description="Error details")


class SheetListResponse(BaseModel):
    """Response model for sheet list API."""

    file_type: str = Field(..., description="File type (xlsx, csv, xlsb)")
    sheets: List[str] = Field(..., description="List of sheet names")


class SheetImageResponse(BaseModel):
    """Response model for sheet image rendering API."""

    image_base64: str = Field(..., description="Base64 encoded PNG image")
    sheet_name: str = Field(..., description="Sheet name")
    row_start: int = Field(..., description="0-based start row index (inclusive)")
    row_end: int = Field(..., description="0-based end row index (inclusive)")
    col_start: int = Field(..., description="0-based start column index (inclusive)")
    col_end: int = Field(..., description="0-based end column index (inclusive)")
    row_height_px: int = Field(..., description="Row height in pixels")
    col_width_px: int = Field(..., description="Column width in pixels")


class DataFrameResponse(BaseModel):
    """Response model for DataFrame building API."""

    dataset_id: str = Field(..., description="Dataset identifier for future Chat with Data")
    columns: List[str] = Field(..., description="Column names")
    preview_rows: List[List[Optional[Any]]] = Field(..., description="Preview data rows (2D array)")
    n_rows: int = Field(..., description="Total number of rows in DataFrame")
    n_cols: int = Field(..., description="Total number of columns in DataFrame")
    file_name: str = Field(..., description="Original file name")
    sheet_name: str = Field(..., description="Sheet name")
    header_row_number: int = Field(..., description="Header row number (1-based)")


# Chat with Data schemas
class ColumnInfo(BaseModel):
    """Column information for table schema."""

    name: str = Field(..., description="Column name")
    dtype: str = Field(..., description="Data type (e.g., 'int64', 'object', 'float64')")
    chinese_description: Optional[str] = Field(None, description="Chinese description of the column")
    sample_values: List[Any] = Field(default_factory=list, description="Sample values from the column")
    stats: Optional[Dict[str, Any]] = Field(None, description="Column statistics (min, max, n_unique, etc.)")


class TableSchema(BaseModel):
    """Table schema information."""

    table_id: str = Field(..., description="Table identifier")
    columns: List[ColumnInfo] = Field(..., description="List of column information")
    n_rows: int = Field(..., description="Total number of rows")
    n_cols: int = Field(..., description="Total number of columns")


class ChatInitRequest(BaseModel):
    """Request model for chat initialization."""

    table_id: str = Field(..., description="Table identifier")
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class ChatInitResponse(BaseModel):
    """Response model for chat initialization."""

    session_id: str = Field(..., description="Chat session identifier")
    table_schema: TableSchema = Field(..., description="Table schema information")


class ChatMessageRequest(BaseModel):
    """Request model for chat message."""

    session_id: str = Field(..., description="Chat session identifier")
    user_query: str = Field(..., description="User query text")


class FinalAnswer(BaseModel):
    """Final answer structure."""

    text: str = Field(..., description="Natural language summary and explanation")
    pandas_code: str = Field(..., description="Complete pandas code string")


class ChatMessageResponse(BaseModel):
    """Response model for chat message."""

    final_answer: FinalAnswer = Field(..., description="Final answer with text and code")
    thinking_summary: List[str] = Field(..., description="Simplified thinking process steps")
    debug: Optional[Dict[str, Any]] = Field(None, description="Debug information (plan_raw, etc.)")

