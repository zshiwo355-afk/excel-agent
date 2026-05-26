import json
from typing import Any

from openai import OpenAI

from app.config import get_settings


SYSTEM_PROMPT = """你是 ExcelPlan 生成器。
你只能返回 JSON。
不要返回 markdown。
不要返回解释。
不要返回额外前后缀。
不要把 action 作为对象 key。
必须使用下面格式：
{
  "action": "modify_workbook",
  "workbook_name": "处理结果",
  "sheets": [
    {
      "operation": "format_and_sort_sheet",
      "name": "原始数据",
      "source_sheet": "原始数据",
      "header_row": 4,
      "data_start_row": 5,
      "columns": [],
      "sample_rows": 0,
      "group_by": [],
      "metrics": [],
      "sort": {
        "column": "价格",
        "order": "desc",
        "numeric": true
      },
      "clean": {
        "remove_empty_rows": false,
        "trim_text": false
      },
      "style": {
        "freeze_header": true,
        "auto_filter": true,
        "auto_width": true,
        "header_bold": true
      }
    }
  ],
  "notes": []
}
如果用户上传了文件：
- action 必须优先用 modify_workbook
- source_sheet 必须从 workbook_context.sheet_names 中选择
- 如果 workbook_context 中有 header_row 和 data_start_row，必须使用它们
- 字段名必须尽量使用 workbook_context 中真实存在的 headers
- 如果只是美化表格，用 operation=format_sheet
- 如果用户要求排序，必须生成 sort 字段和 operation=sort_rows 或 format_and_sort_sheet
- 如果用户要求清洗，必须生成 clean 字段和 operation=clean_sheet
- notes 不能包含要执行的操作
- 如果是新增汇总，用 operation=create_summary_sheet
- 如果是新增字段，用 operation=append_columns
如果用户没有上传文件：
- action 必须用 create_workbook
- 至少创建一个 sheet
- 每个 sheet 必须有 name 和 columns
"""


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _client(self) -> OpenAI:
        if not self.settings.deepseek_api_key:
            raise RuntimeError(
                "DeepSeek API is not configured. Please set DEEPSEEK_API_KEY in backend/.env."
            )
        return OpenAI(
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url,
        )

    def generate_excel_plan(
        self,
        message: str,
        workbook_context: dict[str, Any] | None,
        uploaded_file_path: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any] | str]:
        if self.settings.use_mock_llm:
            raw = self._mock_excel_plan(message, workbook_context, uploaded_file_path)
            return self.normalize_excel_plan(raw, message, workbook_context), raw

        client = self._client()
        user_payload = {
            "user_request": message,
            "uploaded_file_path": uploaded_file_path,
            "workbook_context": workbook_context,
            "output_constraints": {
                "supported_actions": ["create_workbook", "modify_workbook"],
                "supported_operations": [
                    "create_sheet",
                    "append_columns",
                    "create_summary_sheet",
                    "format_sheet",
                    "sort_rows",
                    "clean_sheet",
                    "format_and_sort_sheet",
                ],
                "supported_style_options": [
                    "freeze_header",
                    "auto_filter",
                    "auto_width",
                    "header_bold",
                ],
                "sheet_name_max_length": 31,
            },
        }

        response = client.chat.completions.create(
            model=self.settings.deepseek_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0.1,
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("DeepSeek returned an empty response.")

        raw_json = json.loads(content)
        normalized = self.normalize_excel_plan(raw_json, message, workbook_context)
        return normalized, raw_json

    def normalize_excel_plan(
        self,
        raw_json: dict[str, Any],
        user_input: str,
        workbook_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if all(key in raw_json for key in ("action", "workbook_name", "sheets")):
            return raw_json

        if "modify_workbook" in raw_json and isinstance(raw_json["modify_workbook"], dict):
            return self._normalize_legacy_modify(
                raw_json["modify_workbook"],
                user_input,
                workbook_context,
            )

        if "create_workbook" in raw_json and isinstance(raw_json["create_workbook"], dict):
            return self._normalize_legacy_create(raw_json["create_workbook"], user_input)

        raise ValueError(
            "LLM returned invalid ExcelPlan. Missing required fields: action, workbook_name, sheets."
        )

    def _normalize_legacy_modify(
        self,
        payload: dict[str, Any],
        user_input: str,
        workbook_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        sheets = payload.get("sheets")
        if not sheets:
            sheets = self._build_fallback_modify_sheets(user_input, workbook_context)
        return {
            "action": "modify_workbook",
            "workbook_name": payload.get("workbook_name") or "处理结果.xlsx",
            "sheets": sheets,
            "notes": payload.get("notes", []),
        }

    def _normalize_legacy_create(
        self,
        payload: dict[str, Any],
        user_input: str,
    ) -> dict[str, Any]:
        sheets = payload.get("sheets")
        if not sheets:
            sheets = self._build_fallback_create_sheets(user_input)
        return {
            "action": "create_workbook",
            "workbook_name": payload.get("workbook_name") or "新建表格.xlsx",
            "sheets": sheets,
            "notes": payload.get("notes", []),
        }

    def _build_fallback_modify_sheets(
        self,
        user_input: str,
        workbook_context: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        source_sheet = self._pick_source_sheet(workbook_context)
        if not source_sheet:
            raise ValueError(
                "LLM returned invalid ExcelPlan. Missing required fields: action, workbook_name, sheets."
            )

        sheet_context = self._pick_sheet_context(workbook_context, source_sheet)
        header_row = sheet_context.get("header_row") if sheet_context else 1
        data_start_row = sheet_context.get("data_start_row") if sheet_context else 2

        if any(keyword in user_input for keyword in ["汇总", "统计", "合计", "summary", "Summary"]):
            headers = self._pick_headers(workbook_context, source_sheet)
            group_by = headers[:1] or ["分类"]
            metric_source = headers[1] if len(headers) > 1 else (headers[0] if headers else "数值")
            return [
                {
                    "operation": "create_summary_sheet",
                    "name": "汇总",
                    "source_sheet": source_sheet,
                    "header_row": header_row,
                    "data_start_row": data_start_row,
                    "columns": [],
                    "sample_rows": 0,
                    "group_by": group_by,
                    "metrics": [
                        {
                            "name": f"{metric_source}合计",
                            "source_column": metric_source,
                            "aggregation": "sum",
                        }
                    ],
                    "style": {
                        "freeze_header": True,
                        "auto_filter": True,
                        "auto_width": True,
                        "header_bold": True,
                    },
                }
            ]

        sort_column = self._detect_sort_column(user_input, workbook_context, source_sheet)
        if sort_column:
            return [
                {
                    "operation": "format_and_sort_sheet",
                    "name": source_sheet,
                    "source_sheet": source_sheet,
                    "header_row": header_row,
                    "data_start_row": data_start_row,
                    "columns": [],
                    "sample_rows": 0,
                    "group_by": [],
                    "metrics": [],
                    "sort": {
                        "column": sort_column,
                        "order": "desc" if any(keyword in user_input for keyword in ["从高到低", "降序", "desc"]) else "asc",
                        "numeric": True,
                    },
                    "style": {
                        "freeze_header": True,
                        "auto_filter": True,
                        "auto_width": True,
                        "header_bold": True,
                    },
                }
            ]

        return [
            {
                "operation": "format_sheet",
                "name": source_sheet,
                "source_sheet": source_sheet,
                "header_row": header_row,
                "data_start_row": data_start_row,
                "columns": [],
                "sample_rows": 0,
                "group_by": [],
                "metrics": [],
                "clean": {
                    "remove_empty_rows": False,
                    "trim_text": False,
                },
                "style": {
                    "freeze_header": True,
                    "auto_filter": True,
                    "auto_width": True,
                    "header_bold": True,
                },
            }
        ]

    def _build_fallback_create_sheets(self, user_input: str) -> list[dict[str, Any]]:
        return [
            {
                "operation": "create_sheet",
                "name": "Sheet1",
                "columns": self._extract_columns_from_message(user_input) or ["字段1", "字段2", "字段3"],
                "sample_rows": 5,
                "style": {
                    "freeze_header": True,
                    "auto_filter": True,
                    "auto_width": True,
                    "header_bold": True,
                },
            }
        ]

    def _extract_columns_from_message(self, user_input: str) -> list[str]:
        if "包含" not in user_input:
            return []
        after = user_input.split("包含", 1)[1]
        normalized = after.replace("，", ",").replace("、", ",").replace("。", ",")
        return [item.strip() for item in normalized.split(",") if item.strip()]

    def _pick_source_sheet(self, workbook_context: dict[str, Any] | None) -> str | None:
        sheet_names = (workbook_context or {}).get("sheet_names", [])
        return sheet_names[0] if sheet_names else None

    def _pick_headers(self, workbook_context: dict[str, Any] | None, source_sheet: str) -> list[str]:
        for sheet in (workbook_context or {}).get("sheets", []):
            if sheet.get("name") == source_sheet:
                return sheet.get("headers", [])
        return []

    def _pick_sheet_context(
        self,
        workbook_context: dict[str, Any] | None,
        source_sheet: str,
    ) -> dict[str, Any]:
        for sheet in (workbook_context or {}).get("sheets", []):
            if sheet.get("name") == source_sheet:
                return sheet
        return {}

    def _detect_sort_column(
        self,
        user_input: str,
        workbook_context: dict[str, Any] | None,
        source_sheet: str,
    ) -> str | None:
        if not any(keyword in user_input for keyword in ["排序", "从高到低", "从低到高", "升序", "降序"]):
            return None
        headers = self._pick_headers(workbook_context, source_sheet)
        for header in headers:
            if header and header in user_input:
                return header
        if "价格" in user_input:
            for header in headers:
                if "价格" in header or "金价" in header:
                    return header
        return None

    def _mock_excel_plan(
        self,
        message: str,
        workbook_context: dict[str, Any] | None,
        uploaded_file_path: str | None,
    ) -> dict[str, Any]:
        if uploaded_file_path and workbook_context:
            source_sheet = self._pick_source_sheet(workbook_context) or "Sheet1"
            sheet_context = self._pick_sheet_context(workbook_context, source_sheet)
            sort_column = self._detect_sort_column(message, workbook_context, source_sheet)
            return {
                "action": "modify_workbook",
                "workbook_name": "mock_处理结果.xlsx",
                "sheets": [
                    {
                        "operation": "format_and_sort_sheet" if sort_column else "format_sheet",
                        "name": source_sheet,
                        "source_sheet": source_sheet,
                        "header_row": sheet_context.get("header_row", 1),
                        "data_start_row": sheet_context.get("data_start_row", 2),
                        "columns": [],
                        "sample_rows": 0,
                        "group_by": [],
                        "metrics": [],
                        "sort": {
                            "column": sort_column,
                            "order": "desc",
                            "numeric": True,
                        }
                        if sort_column
                        else None,
                        "clean": {
                            "remove_empty_rows": False,
                            "trim_text": False,
                        },
                        "style": {
                            "freeze_header": True,
                            "auto_filter": True,
                            "auto_width": True,
                            "header_bold": True,
                        },
                    }
                ],
                "notes": [] if sort_column else ["未能确定排序列"],
            }

        return {
            "action": "create_workbook",
            "workbook_name": "mock_新建表格.xlsx",
            "sheets": [
                {
                    "operation": "create_sheet",
                    "name": "明细",
                    "columns": self._extract_columns_from_message(message) or ["字段1", "字段2", "字段3"],
                    "sample_rows": 5,
                    "style": {
                        "freeze_header": True,
                        "auto_filter": True,
                        "auto_width": True,
                        "header_bold": True,
                    },
                }
            ],
            "notes": ["mock llm enabled"],
        }


llm_service = LLMService()
