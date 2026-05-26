from pathlib import Path

from openpyxl import Workbook

from app.excel_tools.merger import merge_workbooks_by_plan
from app.excel_tools.profiler import profile_workbook
from app.excel_tools.validator import validate_output_workbook
from app.schemas.excel_plan import ExcelPlan


BASE_DIR = Path(__file__).resolve().parent
TMP_DIR = BASE_DIR / "storage" / "tmp_merge_test"


def write_workbook(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def run_same_headers_case() -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    file1 = TMP_DIR / "file1.xlsx"
    file2 = TMP_DIR / "file2.xlsx"
    output = TMP_DIR / "merged_same_headers.xlsx"

    write_workbook(file1, ["日期", "门店", "金额"], [["2026-05-01", "A店", 10], ["2026-05-02", "B店", 20]])
    write_workbook(
        file2,
        ["日期", "门店", "金额"],
        [["2026-05-03", "C店", 30], ["2026-05-04", "D店", 40], ["2026-05-05", "E店", 50]],
    )

    workbook_contexts = [
        profile_workbook(file1, file_id="file_1", file_name="file1.xlsx"),
        profile_workbook(file2, file_id="file_2", file_name="file2.xlsx"),
    ]
    plan = ExcelPlan.model_validate(
        {
            "action": "merge_workbooks",
            "workbook_name": "merged_same_headers.xlsx",
            "sheets": [],
            "merge": {
                "mode": "append_rows",
                "target_sheet_name": "合并明细",
                "source_sheets": [
                    {
                        "file_id": "file_1",
                        "file_name": "file1.xlsx",
                        "sheet_name": "Sheet1",
                        "header_row": 1,
                        "data_start_row": 2,
                    },
                    {
                        "file_id": "file_2",
                        "file_name": "file2.xlsx",
                        "sheet_name": "Sheet1",
                        "header_row": 1,
                        "data_start_row": 2,
                    },
                ],
                "column_mapping": {"日期": ["日期"], "门店": ["门店"], "金额": ["金额"]},
                "add_source_columns": True,
                "source_columns": ["来源文件", "来源Sheet"],
            },
            "style": {
                "freeze_header": True,
                "auto_filter": True,
                "auto_width": True,
                "header_bold": True,
            },
            "notes": [],
        }
    )
    merge_workbooks_by_plan(plan, workbook_contexts, output)
    validation = validate_output_workbook(output, plan, workbook_contexts)
    assert validation["ok"], validation
    assert validation["expected_rows"] == 5, validation
    assert validation["actual_rows"] == 5, validation


def run_mapped_headers_case() -> None:
    file1 = TMP_DIR / "mapped1.xlsx"
    file2 = TMP_DIR / "mapped2.xlsx"
    output = TMP_DIR / "merged_mapped_headers.xlsx"

    write_workbook(file1, ["门店名称", "产品", "金额"], [["A店", "商品A", 10], ["B店", "商品B", 20]])
    write_workbook(file2, ["药店名称", "商品名称", "销售额"], [["C店", "商品C", 30]])

    workbook_contexts = [
        profile_workbook(file1, file_id="file_1", file_name="mapped1.xlsx"),
        profile_workbook(file2, file_id="file_2", file_name="mapped2.xlsx"),
    ]
    plan = ExcelPlan.model_validate(
        {
            "action": "merge_workbooks",
            "workbook_name": "merged_mapped_headers.xlsx",
            "sheets": [],
            "merge": {
                "mode": "append_rows",
                "target_sheet_name": "合并明细",
                "source_sheets": [
                    {
                        "file_id": "file_1",
                        "file_name": "mapped1.xlsx",
                        "sheet_name": "Sheet1",
                        "header_row": 1,
                        "data_start_row": 2,
                    },
                    {
                        "file_id": "file_2",
                        "file_name": "mapped2.xlsx",
                        "sheet_name": "Sheet1",
                        "header_row": 1,
                        "data_start_row": 2,
                    },
                ],
                "column_mapping": {
                    "门店名称": ["门店名称", "药店名称"],
                    "产品": ["产品", "商品名称"],
                    "金额": ["金额", "销售额"],
                },
                "add_source_columns": True,
                "source_columns": ["来源文件", "来源Sheet"],
            },
            "style": {
                "freeze_header": True,
                "auto_filter": True,
                "auto_width": True,
                "header_bold": True,
            },
            "notes": [],
        }
    )
    merge_workbooks_by_plan(plan, workbook_contexts, output)
    validation = validate_output_workbook(output, plan, workbook_contexts)
    assert validation["ok"], validation


if __name__ == "__main__":
    run_same_headers_case()
    run_mapped_headers_case()
    print("merge mvp tests passed")
