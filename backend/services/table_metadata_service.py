"""Service for managing table metadata (schema, statistics, etc.)."""

import logging
from typing import Dict, List, Optional, Any
import pandas as pd

from backend.models.schemas import ColumnInfo, TableSchema

logger = logging.getLogger(__name__)


class TableMetadataService:
    """Service for storing and retrieving table metadata."""

    def __init__(self):
        """Initialize the metadata service with in-memory storage."""
        # In-memory storage: table_id -> TableSchema
        self._tables: Dict[str, TableSchema] = {}
        # In-memory storage: table_id -> DataFrame (for execution)
        self._dataframes: Dict[str, pd.DataFrame] = {}

    def register_table(
        self,
        table_id: str,
        df: pd.DataFrame,
        column_descriptions: Optional[Dict[str, str]] = None,
    ) -> TableSchema:
        """
        Register a table with its metadata.

        Args:
            table_id: Table identifier
            df: Pandas DataFrame
            column_descriptions: Optional dictionary mapping column names to Chinese descriptions

        Returns:
            TableSchema object
        """
        logger.info(f"Registering table: table_id={table_id}, shape={df.shape}")

        # Build column info
        columns: List[ColumnInfo] = []
        for col_name in df.columns:
            col_series = df[col_name]

            # Get dtype
            dtype_str = str(col_series.dtype)

            # Get sample values (non-null, up to 5)
            sample_values = col_series.dropna().head(5).tolist()

            # Calculate statistics
            stats: Dict[str, Any] = {}
            if pd.api.types.is_numeric_dtype(col_series):
                stats["min"] = float(col_series.min()) if not col_series.empty else None
                stats["max"] = float(col_series.max()) if not col_series.empty else None
                stats["mean"] = float(col_series.mean()) if not col_series.empty else None
            stats["n_unique"] = int(col_series.nunique())
            stats["n_null"] = int(col_series.isna().sum())

            # Get Chinese description
            chinese_desc = None
            if column_descriptions and col_name in column_descriptions:
                chinese_desc = column_descriptions[col_name]

            column_info = ColumnInfo(
                name=col_name,
                dtype=dtype_str,
                chinese_description=chinese_desc,
                sample_values=sample_values,
                stats=stats,
            )
            columns.append(column_info)

        # Create table schema
        table_schema = TableSchema(
            table_id=table_id,
            columns=columns,
            n_rows=len(df),
            n_cols=len(df.columns),
        )

        # Store
        self._tables[table_id] = table_schema
        self._dataframes[table_id] = df.copy()

        logger.info(f"Table registered: table_id={table_id}, columns={len(columns)}")
        return table_schema

    def get_table_schema(self, table_id: str) -> Optional[TableSchema]:
        """
        Get table schema by table_id.

        Args:
            table_id: Table identifier

        Returns:
            TableSchema if found, None otherwise
        """
        return self._tables.get(table_id)

    def get_dataframe(self, table_id: str) -> Optional[pd.DataFrame]:
        """
        Get DataFrame by table_id.

        Args:
            table_id: Table identifier

        Returns:
            DataFrame if found, None otherwise
        """
        df = self._dataframes.get(table_id)
        if df is not None:
            return df.copy()  # Return a copy to avoid mutations
        return None

    def table_exists(self, table_id: str) -> bool:
        """
        Check if a table exists.

        Args:
            table_id: Table identifier

        Returns:
            True if table exists, False otherwise
        """
        return table_id in self._tables


# Global instance
_metadata_service = TableMetadataService()


def get_metadata_service() -> TableMetadataService:
    """Get the global metadata service instance."""
    return _metadata_service

