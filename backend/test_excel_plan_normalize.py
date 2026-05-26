from app.schemas.excel_plan import ExcelPlan
from app.services.llm_service import llm_service


def run_normalize_test() -> None:
    raw_llm_response = {
        "action": "modify_workbook",
        "workbook_name": "公司拆分结果.xlsx",
        "source_file_id": "file_1",
        "operations": [
            {
                "operation": "split_sheet_by_column",
                "source_sheet": "Sheet1",
                "split_column": "销售客户",
                "split_mode": "sheet_per_value",
                "header_row": 1,
                "data_start_row": 2,
                "style_options": {
                    "freeze_header": True,
                    "auto_filter": True,
                    "auto_width": True,
                    "header_bold": True,
                },
            }
        ],
        "notes": "根据用户要求进行拆分",
    }
    workbook_context = {
        "sheet_names": ["Sheet1"],
        "sheets": [
            {
                "name": "Sheet1",
                "header_row": 1,
                "data_start_row": 2,
                "headers": ["销售客户", "产品", "金额"],
            }
        ],
    }

    normalized = llm_service.normalize_excel_plan(
        raw_llm_response,
        "帮我把里面的公司拆出来，一个公司一个表",
        workbook_context,
        [workbook_context],
    )

    assert "sheets" in normalized
    assert isinstance(normalized["notes"], list)
    assert normalized["notes"] == ["根据用户要求进行拆分"]
    assert normalized["sheets"][0]["operation"] == "split_sheet_by_column"
    assert normalized["sheets"][0]["split"]["column"] == "销售客户"
    assert normalized["sheets"][0]["split"]["target_mode"] == "sheet_per_value"
    assert normalized["sheets"][0]["style"]["freeze_header"] is True
    ExcelPlan.model_validate(normalized)


if __name__ == "__main__":
    run_normalize_test()
    print("excel plan normalize test passed")
