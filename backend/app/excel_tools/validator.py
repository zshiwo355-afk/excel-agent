from pathlib import Path
from typing import Any

from app.excel_tools.reader import load_workbook_safe
from app.schemas.excel_plan import ExcelPlan


def _coerce_sort_value(value, numeric: bool):
    if value is None:
        return float("-inf") if numeric else ""
    if not numeric:
        return str(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.replace("楼", "").replace("元", "").replace(",", "").strip()
        try:
            return float(normalized)
        except ValueError:
            return float("-inf")
    return float("-inf")


def _expected_merge_rows(plan: ExcelPlan, workbook_contexts: list[dict[str, Any]]) -> int:
    if not plan.merge:
        return 0
    expected_rows = 0
    workbook_index = {workbook.get("file_id"): workbook for workbook in workbook_contexts}
    for source_sheet in plan.merge.source_sheets:
        workbook_context = workbook_index.get(source_sheet.file_id)
        if not workbook_context:
            continue
        workbook = load_workbook_safe(workbook_context.get("file_path"), data_only=True)
        sheet = workbook[source_sheet.sheet_name]
        for row_idx in range(source_sheet.data_start_row, sheet.max_row + 1):
            values = [sheet.cell(row=row_idx, column=col_idx).value for col_idx in range(1, sheet.max_column + 1)]
            if any(value not in (None, "") for value in values):
                expected_rows += 1
    return expected_rows


def _validate_sorting(workbook, plan: ExcelPlan) -> dict[str, Any] | None:
    for sheet_plan in plan.sheets:
        target_name = sheet_plan.source_sheet or sheet_plan.name
        if target_name not in workbook.sheetnames:
            continue
        sheet = workbook[target_name]

        if sheet_plan.style:
            if sheet_plan.style.freeze_header and sheet.freeze_panes != "A2":
                return {"ok": False, "message": f"Sheet '{target_name}' freeze_header validation failed."}
            if sheet_plan.style.auto_filter and not sheet.auto_filter.ref:
                return {"ok": False, "message": f"Sheet '{target_name}' auto_filter validation failed."}

        if sheet_plan.sort:
            header_row = sheet_plan.header_row or 1
            data_start_row = sheet_plan.data_start_row or (header_row + 1)
            data_end_row = sheet_plan.data_end_row or sheet.max_row
            sort_col_idx = None
            for col_idx in range(1, sheet.max_column + 1):
                value = sheet.cell(row=header_row, column=col_idx).value
                if value is not None and str(value).strip() == sheet_plan.sort.column:
                    sort_col_idx = col_idx
                    break
            if sort_col_idx is None:
                return {"ok": False, "message": f"Sort validation failed: column '{sheet_plan.sort.column}' not found."}

            values = [
                _coerce_sort_value(sheet.cell(row=row_idx, column=sort_col_idx).value, sheet_plan.sort.numeric)
                for row_idx in range(data_start_row, data_end_row + 1)
            ]
            ordered = sorted(values, reverse=sheet_plan.sort.order == "desc")
            if values != ordered:
                return {
                    "ok": False,
                    "message": f"Sort validation failed for sheet '{target_name}' on column '{sheet_plan.sort.column}'.",
                }
    return None


def _validate_merge_output(workbook, plan: ExcelPlan, workbook_contexts: list[dict[str, Any]]) -> dict[str, Any]:
    if not plan.merge:
        return {"ok": False, "message": "Merge plan is missing."}
    target_sheet_name = plan.merge.target_sheet_name
    if target_sheet_name not in workbook.sheetnames:
        return {"ok": False, "message": f"Target sheet '{target_sheet_name}' not found."}

    sheet = workbook[target_sheet_name]
    if sheet.max_row <= 1:
        return {"ok": False, "message": "Merged output has no data rows.", "expected_rows": 0, "actual_rows": 0}

    headers = [str(sheet.cell(row=1, column=col_idx).value).strip() for col_idx in range(1, sheet.max_column + 1)]
    if plan.merge.add_source_columns:
        for source_column in plan.merge.source_columns:
            if source_column not in headers:
                return {"ok": False, "message": f"Missing source column: {source_column}"}

    actual_rows = 0
    source_file_hits: set[str] = set()
    source_file_col_idx = headers.index(plan.merge.source_columns[0]) + 1 if plan.merge.add_source_columns else None
    for row_idx in range(2, sheet.max_row + 1):
        values = [sheet.cell(row=row_idx, column=col_idx).value for col_idx in range(1, sheet.max_column + 1)]
        if all(value in (None, "") for value in values):
            continue
        actual_rows += 1
        if source_file_col_idx:
            file_name = sheet.cell(row=row_idx, column=source_file_col_idx).value
            if file_name:
                source_file_hits.add(str(file_name))

    expected_rows = _expected_merge_rows(plan, workbook_contexts)
    expected_files = {source.file_name for source in plan.merge.source_sheets}
    if plan.merge.add_source_columns and not expected_files.issubset(source_file_hits):
        return {
            "ok": False,
            "message": "Not every source file appears in 来源文件 column.",
            "expected_rows": expected_rows,
            "actual_rows": actual_rows,
        }
    if expected_rows != actual_rows:
        return {
            "ok": False,
            "message": "Merged row count does not match expected row count.",
            "expected_rows": expected_rows,
            "actual_rows": actual_rows,
        }
    return {"ok": True, "message": "Merge validation passed.", "expected_rows": expected_rows, "actual_rows": actual_rows}


def _validate_split_output(workbook, plan: ExcelPlan) -> dict[str, Any]:
    split_sheet_plan = next((sheet for sheet in plan.sheets if sheet.operation == "split_sheet_by_column"), None)
    if split_sheet_plan is None or split_sheet_plan.split is None or not split_sheet_plan.source_sheet:
        return {"ok": False, "message": "Split plan is missing."}
    source_sheet_name = split_sheet_plan.source_sheet
    split_column = split_sheet_plan.split.column
    split_sheet_names = [name for name in workbook.sheetnames if name != source_sheet_name]
    if not split_sheet_names:
        return {"ok": False, "message": "No split sheets were created."}

    source_row_count = 0
    source_workbook_sheet = workbook[source_sheet_name] if source_sheet_name in workbook.sheetnames else None
    if source_workbook_sheet:
        source_row_count = max(0, source_workbook_sheet.max_row - 1)

    total_split_rows = 0
    for sheet_name in split_sheet_names:
        sheet = workbook[sheet_name]
        if sheet.max_row < 1:
            return {"ok": False, "message": f"Split sheet '{sheet_name}' is empty."}
        headers = [sheet.cell(row=1, column=col_idx).value for col_idx in range(1, sheet.max_column + 1)]
        if not any(header is not None for header in headers):
            return {"ok": False, "message": f"Split sheet '{sheet_name}' is missing headers."}
        split_col_idx = None
        for idx, header in enumerate(headers, start=1):
            if header is not None and str(header).strip() == split_column:
                split_col_idx = idx
                break
        if split_col_idx is None:
            return {"ok": False, "message": f"Split sheet '{sheet_name}' is missing split column '{split_column}'."}
        expected_value = None
        for row_idx in range(2, sheet.max_row + 1):
            row_values = [sheet.cell(row=row_idx, column=col_idx).value for col_idx in range(1, sheet.max_column + 1)]
            if all(value in (None, "") for value in row_values):
                continue
            current_value = sheet.cell(row=row_idx, column=split_col_idx).value
            current_value = "未命名" if current_value in (None, "") else str(current_value).strip()
            if expected_value is None:
                expected_value = current_value
            elif current_value != expected_value:
                return {"ok": False, "message": f"Split sheet '{sheet_name}' contains mixed split values."}
            total_split_rows += 1

    if total_split_rows != source_row_count:
        return {
            "ok": False,
            "message": "Split row count does not match source row count.",
            "expected_rows": source_row_count,
            "actual_rows": total_split_rows,
        }
    return {"ok": True, "message": "Split validation passed.", "expected_rows": source_row_count, "actual_rows": total_split_rows}


def validate_output_workbook(
    file_path: str | Path,
    plan: ExcelPlan | None = None,
    workbook_contexts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        return {"ok": False, "message": "Output workbook file does not exist."}

    try:
        workbook = load_workbook_safe(path, data_only=False)
    except Exception as exc:
        return {"ok": False, "message": f"Unable to open output workbook: {exc}"}

    if not workbook.sheetnames:
        return {"ok": False, "message": "Output workbook must contain at least one sheet."}

    if plan and plan.action == "merge_workbooks":
        return _validate_merge_output(workbook, plan, workbook_contexts or [])

    if plan and any(sheet.operation == "split_sheet_by_column" for sheet in plan.sheets):
        return _validate_split_output(workbook, plan)

    if plan:
        sort_result = _validate_sorting(workbook, plan)
        if sort_result:
            return sort_result

    return {"ok": True, "message": "Workbook validation passed."}
