"""Pydantic schemas for request/response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TablePreviewRow(BaseModel):
    """A single row in the preview data."""

    cells: List[Optional[str]] = Field(..., description="Cell values in the row")


class SheetPreview(BaseModel):
    """Preview data for a sheet."""

    rows: List[List[Optional[str]]] = Field(..., description="Preview rows as 2D list")


class SheetGuessResult(BaseModel):
    """Result of table detection for a single sheet."""

    name: str = Field(..., description="Sheet name")
    is_main: bool = Field(..., description="Whether this is the main sheet")
    header_row_index: int = Field(..., description="0-based index of first header row (for backward compatibility)")
    header_row_indices: List[int] = Field(..., description="0-based indices of all header rows (supports multi-row headers)")
    data_start_row_index: int = Field(..., description="0-based index of first data row")
    detected_columns: List[str] = Field(..., description="Detected column names from header (merged for multi-row headers)")
    preview: SheetPreview = Field(..., description="Preview data")


class GuessTableResponse(BaseModel):
    """Response model for table guessing API."""

    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="File type (xlsx, csv, xlsb)")
    sheets: List[SheetGuessResult] = Field(..., description="Detection results for each sheet")


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

