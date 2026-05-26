from pathlib import Path

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
        normalized = value.replace("¥", "").replace("元", "").replace(",", "").strip()
        try:
            return float(normalized)
        except ValueError:
            return float("-inf")
    return float("-inf")


def validate_output_workbook(file_path: str | Path, plan: ExcelPlan | None = None) -> dict:
    path = Path(file_path)
    if not path.exists():
        return {"ok": False, "message": "Output workbook file does not exist."}

    try:
        workbook = load_workbook_safe(path, data_only=False)
    except Exception as exc:
        return {"ok": False, "message": f"Unable to open output workbook: {exc}"}

    if not workbook.sheetnames:
        return {"ok": False, "message": "Output workbook must contain at least one sheet."}

    if plan:
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

    return {"ok": True, "message": "Workbook validation passed."}
