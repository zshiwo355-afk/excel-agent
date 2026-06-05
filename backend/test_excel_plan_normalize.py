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


def run_template_normalize_test() -> None:
    workbook_contexts = [
        {
            "file_id": "file_1",
            "file_name": "data.xlsx",
            "sheet_names": ["数据表"],
            "sheets": [
                {
                    "name": "数据表",
                    "header_row": 1,
                    "data_start_row": 2,
                    "headers": ["商品", "价格", "地区"],
                }
            ],
        },
        {
            "file_id": "file_2",
            "file_name": "template.xlsx",
            "sheet_names": ["模板表"],
            "sheets": [
                {
                    "name": "模板表",
                    "header_row": 1,
                    "data_start_row": 2,
                    "headers": ["地区", "商品", "价格"],
                }
            ],
        },
    ]

    normalized = llm_service.normalize_excel_plan(
        {},
        "把表A里面的数据按照表B里面的格式进行排序，价格从高到低",
        workbook_contexts[0],
        workbook_contexts,
    )

    assert normalized["action"] == "modify_workbook"
    assert normalized["sheets"][0]["operation"] == "apply_template_sheet"
    assert normalized["sheets"][0]["template"]["template_file_id"] == "file_2"
    assert normalized["sheets"][0]["template"]["source_file_id"] == "file_1"
    assert normalized["sheets"][0]["template"]["column_mapping"]["地区"] == "地区"
    assert normalized["sheets"][0]["sort"]["column"] == "价格"
    assert normalized["sheets"][0]["sort"]["order"] == "desc"
    ExcelPlan.model_validate(normalized)


def run_sort_normalize_test() -> None:
    workbook_context = {
        "sheet_names": ["Sheet1"],
        "sheets": [
            {
                "name": "Sheet1",
                "header_row": 1,
                "data_start_row": 2,
                "headers": ["日期", "黄金价格", "品牌"],
            }
        ],
    }

    normalized_desc = llm_service.normalize_excel_plan(
        {
            "action": "modify_workbook",
            "workbook_name": "排序结果.xlsx",
            "sheets": [{"operation": "sort_rows", "name": "Sheet1", "source_sheet": "Sheet1"}],
        },
        "帮我把价格从高到低进行排序",
        workbook_context,
        [workbook_context],
    )
    assert normalized_desc["sheets"][0]["sort"]["column"] == "黄金价格"
    assert normalized_desc["sheets"][0]["sort"]["order"] == "desc"

    normalized_asc = llm_service.normalize_excel_plan(
        {
            "action": "modify_workbook",
            "workbook_name": "排序结果.xlsx",
            "sheets": [{"operation": "sort_rows", "name": "Sheet1", "source_sheet": "Sheet1"}],
        },
        "帮我把价格从低到高进行排序",
        workbook_context,
        [workbook_context],
    )
    assert normalized_asc["sheets"][0]["sort"]["column"] == "黄金价格"
    assert normalized_asc["sheets"][0]["sort"]["order"] == "asc"
    ExcelPlan.model_validate(normalized_desc)
    ExcelPlan.model_validate(normalized_asc)


def run_today_fill_rewrite_test() -> None:
    workbook_context = {
        "sheet_names": ["今日金价行情"],
        "sheets": [
            {
                "name": "今日金价行情",
                "header_row": 2,
                "data_start_row": 3,
                "headers": ["价格参考", "品类"],
            }
        ],
    }

    normalized = llm_service.normalize_excel_plan(
        {
            "action": "modify_workbook",
            "workbook_name": "处理结果.xlsx",
            "sheets": [
                {
                    "operation": "update_date_month",
                    "name": "今日金价行情",
                    "source_sheet": "今日金价行情",
                    "header_row": 2,
                    "data_start_row": 3,
                    "date_update": {
                        "target_month": 6,
                        "target_columns": [],
                    },
                }
            ],
        },
        "帮我把价格从低到高排序，然后日期就是今天",
        workbook_context,
        [workbook_context],
    )

    assert normalized["action"] == "modify_workbook"
    assert normalized["sheets"][0]["operation"] == "sort_rows"
    assert normalized["sheets"][1]["operation"] == "fill_column_with_value"
    assert normalized["sheets"][1]["fill"]["column_name"] == "日期"
    assert normalized["sheets"][1]["fill"]["value_mode"] == "today_date"
    ExcelPlan.model_validate(normalized)


if __name__ == "__main__":
    run_normalize_test()
    run_template_normalize_test()
    run_sort_normalize_test()
    run_today_fill_rewrite_test()
    print("excel plan normalize test passed")
