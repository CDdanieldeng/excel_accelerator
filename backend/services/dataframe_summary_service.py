"""Service for creating minimal DataFrame summaries for LLM (privacy-safe)."""

import logging
from typing import Any, Dict

import pandas as pd

from backend.models.schemas import DataFrameSummary

logger = logging.getLogger(__name__)


def create_dataframe_summary(df: pd.DataFrame, table_id: str) -> DataFrameSummary:
    """
    Create a minimal, safe summary of DataFrame for LLM.
    
    Only includes:
    - Column names
    - Column data types
    - ONE example row (first non-empty row)
    - Basic metadata (row count, column count)
    
    Does NOT include:
    - Multiple sample rows
    - Statistics (min, max, mean, etc.)
    - Data distribution info
    - Full data access
    
    Args:
        df: Pandas DataFrame
        table_id: Table identifier
        
    Returns:
        DataFrameSummary object with limited information
    """
    logger.info(f"Creating DataFrame summary: table_id={table_id}, shape={df.shape}")
    
    # Extract column names and types
    column_names = df.columns.tolist()
    column_types = {col: str(df[col].dtype) for col in column_names}
    
    # Get ONE example row (first non-empty row)
    example_row: Dict[str, Any] = {}
    for idx, row in df.iterrows():
        if not row.isna().all():  # Skip completely empty rows
            # Convert row to dict, handling NaN values
            example_row = {}
            for col in column_names:
                value = row[col]
                # Convert NaN to None for JSON serialization
                if pd.isna(value):
                    example_row[col] = None
                else:
                    example_row[col] = value
            break
    
    # If no non-empty row found, create empty example
    if not example_row:
        example_row = {col: None for col in column_names}
    
    # Basic metadata only
    metadata: Dict[str, Any] = {
        "n_rows": len(df),
        "n_cols": len(df.columns),
    }
    
    summary = DataFrameSummary(
        table_id=table_id,
        column_names=column_names,
        column_types=column_types,
        example_row=example_row,
        metadata=metadata,
    )
    
    logger.info(f"DataFrame summary created: {len(column_names)} columns, {metadata['n_rows']} rows")
    return summary

