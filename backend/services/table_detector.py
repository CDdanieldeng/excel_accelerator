"""Table header and data region detection service with multi-row header support."""

import logging
from typing import List, Optional, Tuple

from backend.models.schemas import SheetGuessResult, SheetPreview
from backend.config import MAX_HEADER_SEARCH_ROWS

logger = logging.getLogger(__name__)


class TableDetector:
    """Detects table headers and data regions in sheet data, supports multi-row headers."""

    def __init__(self, max_header_search_rows: int = MAX_HEADER_SEARCH_ROWS):
        """
        Initialize the table detector.

        Args:
            max_header_search_rows: Maximum number of rows to search for header
        """
        self.max_header_search_rows = max_header_search_rows

    def _is_numeric(self, value: Optional[str]) -> bool:
        """
        Check if a string value represents a number.

        Args:
            value: String value to check

        Returns:
            True if the value is numeric
        """
        if not value or not value.strip():
            return False
        try:
            float(value.replace(",", "").replace(" ", ""))
            return True
        except (ValueError, AttributeError):
            return False

    def _is_empty_row(self, row: List[Optional[str]]) -> bool:
        """
        Check if a row is empty (all cells are None or empty strings).

        Args:
            row: A row of cell values

        Returns:
            True if the row is empty
        """
        return not any(cell and str(cell).strip() for cell in row)

    def _calculate_header_score(self, row: List[Optional[str]]) -> float:
        """
        Calculate a score indicating how likely a row is to be a header.

        Higher score = more likely to be header.

        Args:
            row: A row of cell values

        Returns:
            Header score (higher is better)
        """
        if not row or self._is_empty_row(row):
            return 0.0

        non_empty_count = sum(1 for cell in row if cell and str(cell).strip())
        if non_empty_count == 0:
            return 0.0

        text_count = 0
        numeric_count = 0

        for cell in row:
            if not cell or not str(cell).strip():
                continue
            cell_str = str(cell).strip()
            if self._is_numeric(cell_str):
                numeric_count += 1
            else:
                text_count += 1

        total_cells = text_count + numeric_count
        if total_cells == 0:
            return 0.0

        # Score: prefer rows with high text ratio and low numeric ratio
        text_ratio = text_count / total_cells
        numeric_ratio = numeric_count / total_cells

        # Base score from text ratio, penalize numeric ratio
        score = text_ratio * 0.7 - numeric_ratio * 0.3

        # Bonus for having multiple non-empty cells (headers usually have multiple columns)
        if non_empty_count >= 3:
            score += 0.2

        return score

    def _calculate_data_score(self, row: List[Optional[str]]) -> float:
        """
        Calculate a score indicating how likely a row is to be data (not header).

        Higher score = more likely to be data.

        Args:
            row: A row of cell values

        Returns:
            Data score (higher is better)
        """
        if not row or self._is_empty_row(row):
            return 0.0

        non_empty_count = sum(1 for cell in row if cell and str(cell).strip())
        if non_empty_count == 0:
            return 0.0

        text_count = 0
        numeric_count = 0

        for cell in row:
            if not cell or not str(cell).strip():
                continue
            cell_str = str(cell).strip()
            if self._is_numeric(cell_str):
                numeric_count += 1
            else:
                text_count += 1

        total_cells = text_count + numeric_count
        if total_cells == 0:
            return 0.0

        # Data rows typically have more numbers and less text
        numeric_ratio = numeric_count / total_cells
        text_ratio = text_count / total_cells

        # Higher numeric ratio = more likely to be data
        score = numeric_ratio * 0.6 + text_ratio * 0.2

        return score

    def _validate_header_candidate(
        self,
        rows: List[List[Optional[str]]],
        header_start: int,
        header_end: int,
        sample_data_rows: int = 5,
    ) -> float:
        """
        Validate a header candidate by checking if subsequent rows look like data.

        Args:
            rows: All rows in the sheet
            header_start: Start index of header region (inclusive)
            header_end: End index of header region (inclusive)
            sample_data_rows: Number of rows after header to check

        Returns:
            Validation score (higher = more confident this is a valid header)
        """
        data_start = header_end + 1
        if data_start >= len(rows):
            return 0.0

        # Check a few rows after the header
        data_scores = []
        for i in range(data_start, min(data_start + sample_data_rows, len(rows))):
            if not self._is_empty_row(rows[i]):
                data_scores.append(self._calculate_data_score(rows[i]))

        if not data_scores:
            return 0.0

        # Average data score - higher means more likely to be real data
        avg_data_score = sum(data_scores) / len(data_scores)

        # Also check that header rows have higher header scores than data rows
        header_scores = []
        for i in range(header_start, header_end + 1):
            if not self._is_empty_row(rows[i]):
                header_scores.append(self._calculate_header_score(rows[i]))

        if not header_scores:
            return 0.0

        avg_header_score = sum(header_scores) / len(header_scores)

        # Validation score: data should look like data, header should look like header
        # And header score should be higher than data score
        validation_score = avg_data_score * 0.5
        if avg_header_score > avg_data_score:
            validation_score += 0.5
        else:
            # Penalty if header score is not higher than data score
            validation_score *= 0.5

        return validation_score

    def _find_header_region(
        self, rows: List[List[Optional[str]]]
    ) -> Tuple[int, int]:
        """
        Find the header region (potentially multiple rows) in the first N rows.

        Args:
            rows: All rows in the sheet

        Returns:
            Tuple of (start_index, end_index) of header region (both inclusive)
        """
        search_rows = min(self.max_header_search_rows, len(rows))
        if search_rows == 0:
            return (0, 0)

        # Step 1: Calculate header scores for all candidate rows
        row_scores: List[Tuple[int, float]] = []
        for i in range(search_rows):
            if self._is_empty_row(rows[i]):
                # Empty rows get very low score
                row_scores.append((i, -1.0))
            else:
                score = self._calculate_header_score(rows[i])
                row_scores.append((i, score))
                logger.debug(f"Row {i} header score: {score:.3f}")

        # Step 2: Find the best single header row (for backward compatibility)
        best_single_row = max(row_scores, key=lambda x: x[1])
        best_single_index = best_single_row[0]
        best_single_score = best_single_row[1]

        # Step 3: Try to find a multi-row header region
        # Look for consecutive rows with high header scores
        header_regions: List[Tuple[int, int, float]] = []  # (start, end, combined_score)

        # Try different header region sizes (1 to 5 rows)
        for region_size in range(1, min(6, search_rows + 1)):
            for start_idx in range(search_rows - region_size + 1):
                end_idx = start_idx + region_size - 1

                # Skip if region contains empty rows (except at boundaries)
                has_empty = False
                for i in range(start_idx + 1, end_idx):
                    if self._is_empty_row(rows[i]):
                        has_empty = True
                        break

                if has_empty:
                    continue

                # Calculate combined score for this region
                region_scores = [row_scores[i][1] for i in range(start_idx, end_idx + 1)]
                avg_score = sum(region_scores) / len(region_scores)

                # Validation: check if rows after this region look like data
                validation_score = self._validate_header_candidate(rows, start_idx, end_idx)

                # Combined score: average header score + validation bonus
                combined_score = avg_score * 0.7 + validation_score * 0.3

                header_regions.append((start_idx, end_idx, combined_score))
                logger.debug(
                    f"Header region [{start_idx}-{end_idx}]: "
                    f"avg_score={avg_score:.3f}, validation={validation_score:.3f}, "
                    f"combined={combined_score:.3f}"
                )

        # Step 4: Choose the best header region
        if header_regions:
            best_region = max(header_regions, key=lambda x: x[2])
            best_start, best_end, best_combined_score = best_region

            # Only use multi-row header if it's significantly better than single row
            # Or if single row score is low (might indicate multi-row header)
            if best_combined_score > best_single_score * 0.9 or best_single_score < 0.3:
                logger.info(
                    f"Detected multi-row header region [{best_start}-{best_end}] "
                    f"(score: {best_combined_score:.3f})"
                )
                return (best_start, best_end)

        # Fall back to single row header
        logger.info(
            f"Detected single-row header at index {best_single_index} "
            f"(score: {best_single_score:.3f})"
        )
        return (best_single_index, best_single_index)

    def _merge_multi_row_header(
        self, header_rows: List[List[Optional[str]]]
    ) -> List[str]:
        """
        Merge multiple header rows into a single list of column names.

        Handles cases like:
        Row 0: [一级标题1]        [一级标题2]
        Row 1: [二级1] [二级2]     [二级3] [二级4]
        Result: [一级标题1/二级1, 一级标题1/二级2, 一级标题2/二级3, 一级标题2/二级4]

        Args:
            header_rows: List of header rows (from top to bottom)

        Returns:
            Merged column names
        """
        if not header_rows:
            return []

        if len(header_rows) == 1:
            # Single row header - just extract non-empty cells
            columns = []
            for cell in header_rows[0]:
                if cell and str(cell).strip():
                    columns.append(str(cell).strip())
                else:
                    columns.append("")
            # Remove trailing empty columns
            while columns and not columns[-1]:
                columns.pop()
            return columns

        # Multi-row header - need to merge
        # Find the maximum number of columns
        max_cols = max(len(row) for row in header_rows)

        # Normalize all rows to the same length
        normalized_rows = []
        for row in header_rows:
            normalized = row + [None] * (max_cols - len(row))
            normalized_rows.append(normalized)

        # Merge strategy: top-down, handling empty cells and merged cells
        merged_columns: List[List[str]] = []  # Each column is a list of parts

        for col_idx in range(max_cols):
            column_parts: List[str] = []
            last_non_empty = None

            # Go from top to bottom
            for row_idx, row in enumerate(normalized_rows):
                cell = row[col_idx] if col_idx < len(row) else None
                cell_str = str(cell).strip() if cell and str(cell).strip() else None

                if cell_str:
                    # If this is the first row or previous cell in this row was empty,
                    # this might be a merged cell spanning multiple columns
                    if row_idx == 0:
                        column_parts.append(cell_str)
                        last_non_empty = cell_str
                    else:
                        # Check if previous row at this column was empty
                        prev_cell = (
                            normalized_rows[row_idx - 1][col_idx]
                            if col_idx < len(normalized_rows[row_idx - 1])
                            else None
                        )
                        prev_cell_str = (
                            str(prev_cell).strip()
                            if prev_cell and str(prev_cell).strip()
                            else None
                        )

                        if prev_cell_str:
                            # Previous row had content - this is a sub-header
                            column_parts.append(cell_str)
                            last_non_empty = cell_str
                        else:
                            # Previous row was empty - might be continuation of merged cell
                            # Check left neighbor
                            left_cell = (
                                row[col_idx - 1] if col_idx > 0 else None
                            )
                            left_cell_str = (
                                str(left_cell).strip()
                                if left_cell and str(left_cell).strip()
                                else None
                            )

                            if left_cell_str and last_non_empty:
                                # This is likely a merged cell - use the last non-empty
                                # Don't add duplicate, but update last_non_empty
                                last_non_empty = cell_str
                            else:
                                column_parts.append(cell_str)
                                last_non_empty = cell_str
                else:
                    # Empty cell - might be part of merged cell from left
                    if row_idx > 0:
                        left_cell = row[col_idx - 1] if col_idx > 0 else None
                        left_cell_str = (
                            str(left_cell).strip()
                            if left_cell and str(left_cell).strip()
                            else None
                        )

                        if left_cell_str and last_non_empty:
                            # This is likely a merged cell - keep the last non-empty
                            pass

            # Join column parts with "/"
            if column_parts:
                merged_col = "/".join(column_parts)
                merged_columns.append(merged_col)
            else:
                merged_columns.append("")

        # Remove trailing empty columns
        while merged_columns and not merged_columns[-1]:
            merged_columns.pop()

        return merged_columns

    def _extract_columns(
        self, header_rows: List[List[Optional[str]]]
    ) -> List[str]:
        """
        Extract column names from header row(s).

        Args:
            header_rows: List of header rows (from top to bottom)

        Returns:
            List of column names
        """
        if len(header_rows) == 1:
            # Single row - simple extraction
            columns: List[str] = []
            for cell in header_rows[0]:
                if cell and str(cell).strip():
                    columns.append(str(cell).strip())
                else:
                    columns.append("")
            # Remove trailing empty columns
            while columns and not columns[-1]:
                columns.pop()
            return columns
        else:
            # Multi-row - merge them
            return self._merge_multi_row_header(header_rows)

    def _count_valid_rows(self, rows: List[List[Optional[str]]], start_index: int) -> int:
        """
        Count rows with at least one non-empty cell.

        Args:
            rows: All rows
            start_index: Starting index to count from

        Returns:
            Number of valid rows
        """
        count = 0
        for i in range(start_index, len(rows)):
            if any(cell and str(cell).strip() for cell in rows[i]):
                count += 1
        return count

    def detect_sheet(
        self,
        sheet_name: str,
        rows: List[List[Optional[str]]],
        max_preview_rows: int = 50,
    ) -> SheetGuessResult:
        """
        Detect table header and data region in a sheet.

        Supports both single-row and multi-row headers.

        Args:
            sheet_name: Name of the sheet
            rows: All rows in the sheet
            max_preview_rows: Maximum number of preview rows to include

        Returns:
            SheetGuessResult with detection results
        """
        logger.info(f"Detecting table in sheet: {sheet_name}, total rows: {len(rows)}")

        if not rows:
            # Empty sheet
            return SheetGuessResult(
                name=sheet_name,
                is_main=False,
                header_row_index=0,
                header_row_indices=[0],
                data_start_row_index=1,
                detected_columns=[],
                preview=SheetPreview(rows=[]),
            )

        # Find header region (can be multiple rows)
        header_start, header_end = self._find_header_region(rows)
        header_row_indices = list(range(header_start, header_end + 1))
        data_start_row_index = header_end + 1

        # Extract header rows
        header_rows = [rows[i] for i in header_row_indices]

        # Extract columns (merged if multi-row)
        detected_columns = self._extract_columns(header_rows)

        logger.info(
            f"Sheet {sheet_name}: header_rows={header_row_indices}, "
            f"data_start={data_start_row_index}, columns={len(detected_columns)}"
        )

        # Generate preview (header rows + data rows)
        preview_rows: List[List[Optional[str]]] = []

        # Add header rows
        for i in header_row_indices:
            if i < len(rows):
                preview_rows.append(rows[i])

        # Add data rows
        for i in range(
            data_start_row_index,
            min(data_start_row_index + max_preview_rows, len(rows)),
        ):
            preview_rows.append(rows[i])

        return SheetGuessResult(
            name=sheet_name,
            is_main=False,  # Will be set by caller based on comparison
            header_row_index=header_start,  # For backward compatibility
            header_row_indices=header_row_indices,
            data_start_row_index=data_start_row_index,
            detected_columns=detected_columns,
            preview=SheetPreview(rows=preview_rows),
        )

    def mark_main_sheet(
        self, results: List[SheetGuessResult], samples: List
    ) -> List[SheetGuessResult]:
        """
        Mark the main sheet based on valid row count.

        Args:
            results: List of detection results
            samples: List of SheetSample objects (for row counting)

        Returns:
            Updated results with is_main flags set
        """
        if len(results) == 1:
            results[0].is_main = True
            return results

        # Count valid rows for each sheet
        sheet_valid_rows: List[int] = []
        for sample in samples:
            valid_count = self._count_valid_rows(sample.rows, 0)
            sheet_valid_rows.append(valid_count)
            logger.info(f"Sheet {sample.name}: {valid_count} valid rows")

        # Find sheet with most valid rows
        max_index = 0
        max_count = sheet_valid_rows[0]
        for i, count in enumerate(sheet_valid_rows):
            if count > max_count:
                max_count = count
                max_index = i

        # Mark main sheet
        for i, result in enumerate(results):
            result.is_main = (i == max_index)

        logger.info(
            f"Marked sheet '{results[max_index].name}' as main (valid rows: {max_count})"
        )
        return results
