import json
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.schemas.task_plan import TaskPlan


SYSTEM_PROMPT = """你是 ExcelPlan 生成器。
你只能返回 JSON，不要返回 markdown，不要返回解释。

规则：
1. 单文件修改时，优先输出 action=modify_workbook。
2. 无上传文件时，输出 action=create_workbook。
3. 多文件合并时，必须输出 action=merge_workbooks。
4. 第一版合并只支持 merge.mode=append_rows。
5. 按字段拆分成多个 sheet 时，必须输出 operation=split_sheet_by_column。
6. notes 只能写解释，不能承载可执行逻辑。
7. source_sheets 必须从 workbook_contexts 中选择，header_row 和 data_start_row 必须使用 profiler 识别结果。
8. 如果字段无法完全对齐，优先保留字段并集，不要失败。
9. 如果用户说一个公司一个表、按公司拆分、按门店拆分、按部门拆分、每个 xxx 一个 sheet，必须生成合法的 action/workbook_name/sheets。
"""

MERGE_KEYWORDS = ["合并", "汇总到一个表", "追加", "整合", "做成总表", "总表"]
SPLIT_KEYWORDS = ["拆出来", "拆分", "一个公司一个表", "每个", "一个表", "一个sheet", "一个 sheet"]
HEADER_ALIASES = {
    "门店名称": ["门店名称", "药店名称", "门店"],
    "地区": ["地区", "区域"],
    "产品": ["产品", "商品", "商品名称"],
    "金额": ["金额", "销售额", "价格"],
    "日期": ["日期", "销售日期"],
}
SPLIT_COLUMN_ALIASES = {
    "公司": ["公司", "公司名称", "企业", "企业名称", "客户公司", "单位", "药店", "门店"],
    "门店": ["门店", "门店名称", "药店", "药店名称"],
    "部门": ["部门", "部门名称"],
}


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
        workbook_contexts: list[dict[str, Any]] | None,
        uploaded_file_path: str | None,
        uploaded_file_paths: list[str] | None,
    ) -> tuple[dict[str, Any], dict[str, Any] | str]:
        if self.settings.use_mock_llm:
            raw = self._mock_excel_plan(
                message,
                workbook_context,
                workbook_contexts,
                uploaded_file_path,
                uploaded_file_paths,
            )
            return self.normalize_excel_plan(raw, message, workbook_context, workbook_contexts), raw

        client = self._client()
        user_payload = {
            "user_request": message,
            "uploaded_file_path": uploaded_file_path,
            "uploaded_file_paths": uploaded_file_paths or [],
            "workbook_context": workbook_context,
            "workbook_contexts": workbook_contexts or [],
            "output_constraints": {
                "supported_actions": ["create_workbook", "modify_workbook", "merge_workbooks"],
                "supported_operations": [
                    "create_sheet",
                    "append_columns",
                    "create_summary_sheet",
                    "format_sheet",
                    "sort_rows",
                    "clean_sheet",
                    "format_and_sort_sheet",
                    "split_sheet_by_column",
                ],
                "supported_merge_modes": ["append_rows"],
                "supported_split_modes": ["sheet_per_value"],
                "supported_style_options": [
                    "freeze_header",
                    "auto_filter",
                    "auto_width",
                    "header_bold",
                ],
                "sheet_name_max_length": 31,
            },
        }

        try:
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
            normalized = self.normalize_excel_plan(raw_json, message, workbook_context, workbook_contexts)
            return normalized, raw_json
        except Exception:
            raw = self._mock_excel_plan(
                message,
                workbook_context,
                workbook_contexts,
                uploaded_file_path,
                uploaded_file_paths,
            )
            return self.normalize_excel_plan(raw, message, workbook_context, workbook_contexts), raw

    def normalize_excel_plan(
        self,
        raw_json: dict[str, Any],
        user_input: str,
        workbook_context: dict[str, Any] | None,
        workbook_contexts: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        normalized_raw = self._coerce_legacy_excel_plan(raw_json)

        if self._is_split_request(user_input, workbook_context):
            if normalized_raw.get("action") and normalized_raw.get("workbook_name") and normalized_raw.get("sheets"):
                return normalized_raw
            return self._build_split_plan(user_input, workbook_context, normalized_raw)

        if self._is_merge_request(user_input, workbook_contexts) and normalized_raw.get("action") != "merge_workbooks":
            return {
                "action": "merge_workbooks",
                "workbook_name": normalized_raw.get("workbook_name") or "合并结果.xlsx",
                "sheets": [],
                "merge": self._build_merge_plan(workbook_contexts or []),
                "style": normalized_raw.get("style") or self._default_style(),
                "notes": normalized_raw.get("notes", []),
            }

        if normalized_raw.get("action") == "merge_workbooks" and normalized_raw.get("workbook_name"):
            normalized_raw["sheets"] = normalized_raw.get("sheets", [])
            normalized_raw["merge"] = normalized_raw.get("merge") or self._build_merge_plan(workbook_contexts or [])
            normalized_raw["style"] = normalized_raw.get("style") or self._default_style()
            return normalized_raw

        if normalized_raw.get("action") and normalized_raw.get("workbook_name"):
            return normalized_raw

        if "merge_workbooks" in normalized_raw and isinstance(normalized_raw["merge_workbooks"], dict):
            return self._normalize_merge(normalized_raw["merge_workbooks"], workbook_contexts)

        if "modify_workbook" in normalized_raw and isinstance(normalized_raw["modify_workbook"], dict):
            return self._normalize_modify(normalized_raw["modify_workbook"], user_input, workbook_context)

        if "create_workbook" in normalized_raw and isinstance(normalized_raw["create_workbook"], dict):
            return self._normalize_create(normalized_raw["create_workbook"], user_input)

        if uploaded_fallback := self._build_fallback_modify_sheets(user_input, workbook_context):
            return {
                "action": "modify_workbook",
                "workbook_name": normalized_raw.get("workbook_name") or "处理结果.xlsx",
                "sheets": uploaded_fallback,
                "notes": normalized_raw.get("notes", []),
            }

        raise ValueError(
            "LLM returned invalid ExcelPlan. Missing required fields: action, workbook_name."
        )

    def _coerce_legacy_excel_plan(self, raw_json: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(raw_json)
        notes = normalized.get("notes")
        if isinstance(notes, str):
            normalized["notes"] = [notes]
        elif isinstance(notes, list):
            normalized["notes"] = [str(item) for item in notes if item not in (None, "")]
        else:
            normalized["notes"] = []

        if "operations" in normalized and "sheets" not in normalized:
            normalized["sheets"] = normalized.get("operations") or []

        if isinstance(normalized.get("sheets"), list):
            normalized["sheets"] = [self._coerce_sheet_operation(item) for item in normalized["sheets"]]

        return normalized

    def _coerce_sheet_operation(self, item: Any) -> dict[str, Any]:
        sheet = dict(item or {})
        if "style_options" in sheet and "style" not in sheet:
            sheet["style"] = sheet.get("style_options")
        if sheet.get("operation") == "split_sheet_by_column":
            if "split" not in sheet and ("split_column" in sheet or "split_mode" in sheet):
                sheet["split"] = {
                    "column": sheet.get("split_column") or "",
                    "target_mode": sheet.get("split_mode") or "sheet_per_value",
                    "include_source_sheet": True,
                    "sanitize_sheet_name": True,
                }
            elif "split" in sheet and isinstance(sheet["split"], dict):
                split = dict(sheet["split"])
                split.setdefault("target_mode", "sheet_per_value")
                split.setdefault("include_source_sheet", True)
                split.setdefault("sanitize_sheet_name", True)
                if "split_column" in sheet and not split.get("column"):
                    split["column"] = sheet.get("split_column")
                sheet["split"] = split
            if not sheet.get("name"):
                sheet["name"] = "按字段拆分" if sheet.get("split") else (sheet.get("source_sheet") or "按字段拆分")
        elif not sheet.get("name"):
            sheet["name"] = sheet.get("source_sheet") or "Sheet1"
        return sheet

    def _default_style(self) -> dict[str, bool]:
        return {
            "freeze_header": True,
            "auto_filter": True,
            "auto_width": True,
            "header_bold": True,
        }

    def _is_merge_request(self, message: str, workbook_contexts: list[dict[str, Any]] | None) -> bool:
        return len(workbook_contexts or []) >= 2 and any(keyword in message for keyword in MERGE_KEYWORDS)

    def _is_split_request(self, message: str, workbook_context: dict[str, Any] | None) -> bool:
        if not workbook_context:
            return False
        lowered = message.lower()
        if "sheet" in lowered and "每个" in message:
            return True
        return any(keyword in message for keyword in SPLIT_KEYWORDS) and any(
            token in message for token in ["公司", "门店", "部门", "药店", "企业", "客户"]
        )

    def _resolve_split_column(self, message: str, workbook_context: dict[str, Any] | None) -> str | None:
        headers = []
        for sheet in (workbook_context or {}).get("sheets", []):
            headers.extend(sheet.get("headers", []))
        unique_headers = [header for header in headers if header]

        requested_group = None
        if any(token in message for token in ["公司", "企业", "单位", "客户"]):
            requested_group = "公司"
        elif any(token in message for token in ["门店", "药店"]):
            requested_group = "门店"
        elif "部门" in message:
            requested_group = "部门"

        if requested_group:
            for alias in SPLIT_COLUMN_ALIASES[requested_group]:
                for header in unique_headers:
                    if header == alias or alias in header:
                        return header

        for header in unique_headers:
            if header in message:
                return header
        return unique_headers[0] if unique_headers else None

    def _build_split_plan(
        self,
        message: str,
        workbook_context: dict[str, Any] | None,
        raw_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source_sheet = self._pick_source_sheet(workbook_context)
        if not source_sheet:
            raise ValueError("未找到可用于拆分的 source_sheet。")
        sheet_context = self._pick_sheet_context(workbook_context, source_sheet)
        split_column = self._resolve_split_column(message, workbook_context)
        if not split_column:
            raise ValueError("未找到用于拆分的字段，请确认表头中是否包含公司/客户/销售客户/门店等字段。")
        workbook_name = (raw_json or {}).get("workbook_name") or f"{split_column}拆分结果.xlsx"
        return {
            "action": "modify_workbook",
            "workbook_name": workbook_name,
            "sheets": [
                {
                    "operation": "split_sheet_by_column",
                    "name": "按字段拆分",
                    "source_sheet": source_sheet,
                    "header_row": sheet_context.get("header_row", 1),
                    "data_start_row": sheet_context.get("data_start_row", 2),
                    "split": {
                        "column": split_column,
                        "target_mode": "sheet_per_value",
                        "include_source_sheet": True,
                        "sanitize_sheet_name": True,
                    },
                    "style": self._default_style(),
                }
            ],
            "notes": (raw_json or {}).get("notes", []),
        }

    def _build_merge_plan(
        self,
        workbook_contexts: list[dict[str, Any]],
        *,
        target_sheet_name: str = "合并明细",
    ) -> dict[str, Any]:
        source_sheets: list[dict[str, Any]] = []
        all_headers: list[str] = []
        for workbook in workbook_contexts:
            first_sheet = (workbook.get("sheets") or [{}])[0]
            source_sheets.append(
                {
                    "file_id": workbook.get("file_id") or "",
                    "file_name": workbook.get("file_name") or "",
                    "sheet_name": first_sheet.get("name") or "Sheet1",
                    "header_row": first_sheet.get("header_row") or 1,
                    "data_start_row": first_sheet.get("data_start_row") or 2,
                }
            )
            for header in first_sheet.get("headers", []):
                if header and header not in all_headers:
                    all_headers.append(header)

        return {
            "mode": "append_rows",
            "target_sheet_name": target_sheet_name,
            "source_sheets": source_sheets,
            "column_mapping": self._build_column_mapping(workbook_contexts, all_headers),
            "add_source_columns": True,
            "source_columns": ["来源文件", "来源Sheet"],
        }

    def _build_column_mapping(
        self,
        workbook_contexts: list[dict[str, Any]],
        all_headers: list[str],
    ) -> dict[str, list[str]]:
        if not workbook_contexts:
            return {}
        mapping: dict[str, list[str]] = {}
        header_pool = {header for header in all_headers if header}
        for target, aliases in HEADER_ALIASES.items():
            matched = [header for header in header_pool if header in aliases]
            if matched:
                mapping[target] = matched
        for header in all_headers:
            mapping.setdefault(header, [header])
        return mapping

    def _normalize_merge(self, payload: dict[str, Any], workbook_contexts: list[dict[str, Any]] | None) -> dict[str, Any]:
        merge = payload.get("merge") or payload
        normalized = self._build_merge_plan(workbook_contexts or [], target_sheet_name=merge.get("target_sheet_name", "合并明细"))
        normalized["column_mapping"] = merge.get("column_mapping") or normalized["column_mapping"]
        normalized["add_source_columns"] = merge.get("add_source_columns", True)
        normalized["source_columns"] = merge.get("source_columns") or ["来源文件", "来源Sheet"]
        return {
            "action": "merge_workbooks",
            "workbook_name": payload.get("workbook_name") or "合并结果.xlsx",
            "sheets": [],
            "merge": normalized,
            "style": payload.get("style") or self._default_style(),
            "notes": payload.get("notes", []),
        }

    def _normalize_modify(
        self,
        payload: dict[str, Any],
        user_input: str,
        workbook_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        normalized_payload = self._coerce_legacy_excel_plan(payload)
        sheets = normalized_payload.get("sheets") or self._build_fallback_modify_sheets(user_input, workbook_context)
        return {
            "action": "modify_workbook",
            "workbook_name": normalized_payload.get("workbook_name") or "处理结果.xlsx",
            "sheets": sheets,
            "notes": normalized_payload.get("notes", []),
        }

    def _normalize_create(self, payload: dict[str, Any], user_input: str) -> dict[str, Any]:
        normalized_payload = self._coerce_legacy_excel_plan(payload)
        sheets = normalized_payload.get("sheets") or self._build_fallback_create_sheets(user_input)
        return {
            "action": "create_workbook",
            "workbook_name": normalized_payload.get("workbook_name") or "新建表格.xlsx",
            "sheets": sheets,
            "notes": normalized_payload.get("notes", []),
        }

    def _build_fallback_modify_sheets(
        self,
        user_input: str,
        workbook_context: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        if self._is_split_request(user_input, workbook_context):
            return self._build_split_plan(user_input, workbook_context)["sheets"]

        source_sheet = self._pick_source_sheet(workbook_context)
        if not source_sheet:
            return []

        sheet_context = self._pick_sheet_context(workbook_context, source_sheet)
        header_row = sheet_context.get("header_row") if sheet_context else 1
        data_start_row = sheet_context.get("data_start_row") if sheet_context else 2

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
                        "order": "desc" if "desc" in user_input or "降序" in user_input else "asc",
                        "numeric": True,
                    },
                    "style": self._default_style(),
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
                "style": self._default_style(),
            }
        ]

    def _build_fallback_create_sheets(self, user_input: str) -> list[dict[str, Any]]:
        return [
            {
                "operation": "create_sheet",
                "name": "Sheet1",
                "columns": self._extract_columns_from_message(user_input) or ["字段1", "字段2", "字段3"],
                "sample_rows": 5,
                "style": self._default_style(),
            }
        ]

    def _extract_columns_from_message(self, user_input: str) -> list[str]:
        if "包含" not in user_input:
            return []
        after = user_input.split("包含", 1)[1]
        normalized = after.replace("，", ",").replace("。", ",").replace("、", ",")
        return [item.strip() for item in normalized.split(",") if item.strip()]

    def _pick_source_sheet(self, workbook_context: dict[str, Any] | None) -> str | None:
        sheet_names = (workbook_context or {}).get("sheet_names", [])
        return sheet_names[0] if sheet_names else None

    def _pick_headers(self, workbook_context: dict[str, Any] | None, source_sheet: str) -> list[str]:
        for sheet in (workbook_context or {}).get("sheets", []):
            if sheet.get("name") == source_sheet:
                return sheet.get("headers", [])
        return []

    def _pick_sheet_context(self, workbook_context: dict[str, Any] | None, source_sheet: str) -> dict[str, Any]:
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
                if "价格" in header or "金额" in header:
                    return header
        return None

    def _mock_excel_plan(
        self,
        message: str,
        workbook_context: dict[str, Any] | None,
        workbook_contexts: list[dict[str, Any]] | None,
        uploaded_file_path: str | None,
        uploaded_file_paths: list[str] | None,
    ) -> dict[str, Any]:
        contexts = workbook_contexts or ([workbook_context] if workbook_context else [])
        if self._is_split_request(message, workbook_context):
            return self._build_split_plan(message, workbook_context)
        if self._is_merge_request(message, contexts):
            return {
                "action": "merge_workbooks",
                "workbook_name": "mock_合并结果.xlsx",
                "sheets": [],
                "merge": self._build_merge_plan(contexts),
                "style": self._default_style(),
                "notes": ["mock llm enabled"],
            }
        if uploaded_file_path and workbook_context:
            return {
                "action": "modify_workbook",
                "workbook_name": "mock_处理结果.xlsx",
                "sheets": self._build_fallback_modify_sheets(message, workbook_context),
                "notes": ["mock llm enabled"],
            }
        return {
            "action": "create_workbook",
            "workbook_name": "mock_新建表格.xlsx",
            "sheets": self._build_fallback_create_sheets(message),
            "notes": ["mock llm enabled"],
        }

    def generate_task_plan(
        self,
        message: str,
        workbook_contexts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if self.settings.use_mock_llm or not self.settings.deepseek_api_key:
            return self._mock_task_plan(message, workbook_contexts)

        client = self._client()
        prompt = {
            "goal": message,
            "workbook_contexts": workbook_contexts,
            "requirements": {
                "task_type": "complex_excel_workflow",
                "must_split_into_steps": True,
                "step_types": [
                    "analyze_files",
                    "confirm_column_mapping",
                    "merge_workbooks",
                    "deduplicate_rows",
                    "clean_rows",
                    "create_summary_sheet",
                    "sort_rows",
                    "format_sheet",
                    "create_chart",
                    "create_exception_sheet",
                    "validate_workbook",
                    "export_workbook",
                ],
            },
        }
        try:
            response = client.chat.completions.create(
                model=self.settings.deepseek_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "你是 TaskPlan 生成器，只返回 JSON，必须拆成多个 StepPlan。"},
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("DeepSeek returned an empty TaskPlan response.")
            return TaskPlan.model_validate(json.loads(content)).model_dump(mode="json")
        except Exception:
            return self._mock_task_plan(message, workbook_contexts)

    def _mock_task_plan(self, message: str, workbook_contexts: list[dict[str, Any]]) -> dict[str, Any]:
        merge_plan = self._build_merge_plan(workbook_contexts, target_sheet_name="合并明细")
        mapping_uncertain = len({
            tuple(((workbook.get("sheets") or [{}])[0].get("headers") or []))
            for workbook in workbook_contexts
        }) > 1
        needs_dedup = any(keyword in message for keyword in ["去重", "重复"])
        needs_summary = any(keyword in message for keyword in ["汇总", "汇总 sheet", "汇总表"])
        steps: list[dict[str, Any]] = [
            {
                "step_id": "step_1",
                "step_type": "analyze_files",
                "title": "分析上传文件",
                "description": "读取上传工作簿结构和表头信息。",
                "output_artifact": "analyzed_workbooks",
                "params": {},
                "validation": {"workbook_count_min": 1},
            }
        ]
        next_id = 2
        if mapping_uncertain or "字段对齐" in message or "字段映射" in message:
            steps.append(
                {
                    "step_id": f"step_{next_id}",
                    "step_type": "confirm_column_mapping",
                    "title": "确认字段映射",
                    "description": "确认用于合并的字段映射。",
                    "input_artifact": "analyzed_workbooks",
                    "output_artifact": "confirmed_column_mapping",
                    "params": {"column_mapping": merge_plan["column_mapping"]},
                    "validation": {"mapping_count_min": 1},
                    "requires_user_confirm": True,
                }
            )
            next_id += 1
        steps.append(
            {
                "step_id": f"step_{next_id}",
                "step_type": "merge_workbooks",
                "title": "合并工作簿",
                "description": "纵向追加多个 Excel 数据到总表。",
                "input_artifact": "analyzed_workbooks",
                "output_artifact": "raw_merged_workbook",
                "params": {"merge_plan": merge_plan},
                "validation": {"target_sheet_name": "合并明细"},
            }
        )
        next_id += 1
        if needs_dedup:
            steps.append(
                {
                    "step_id": f"step_{next_id}",
                    "step_type": "deduplicate_rows",
                    "title": "去除重复数据",
                    "description": "对合并后的明细数据去重。",
                    "input_artifact": "raw_merged_workbook",
                    "output_artifact": "deduplicated_workbook",
                    "params": {"sheet_name": "合并明细", "dedupe_columns": ["门店名称", "地区", "产品", "金额"]},
                    "validation": {"duplicate_rows_should_decrease": True},
                }
            )
            next_id += 1
        if needs_summary:
            steps.append(
                {
                    "step_id": f"step_{next_id}",
                    "step_type": "create_summary_sheet",
                    "title": "生成汇总 Sheet",
                    "description": "按地区汇总销售额。",
                    "input_artifact": "deduplicated_workbook" if needs_dedup else "raw_merged_workbook",
                    "output_artifact": "summary_workbook",
                    "params": {
                        "source_sheet": "合并明细",
                        "target_sheet": "地区汇总",
                        "group_by": ["地区"],
                        "metric_column": "金额",
                        "metric_name": "销售额合计",
                    },
                    "validation": {"sheet_name": "地区汇总"},
                }
            )
            next_id += 1
        steps.append(
            {
                "step_id": f"step_{next_id}",
                "step_type": "format_sheet",
                "title": "格式化输出",
                "description": "统一格式化输出工作簿。",
                "input_artifact": "summary_workbook" if needs_summary else "deduplicated_workbook" if needs_dedup else "raw_merged_workbook",
                "output_artifact": "formatted_workbook",
                "params": {"sheet_names": ["合并明细", "地区汇总"]},
                "validation": {"formatted": True},
            }
        )
        next_id += 1
        steps.append(
            {
                "step_id": f"step_{next_id}",
                "step_type": "validate_workbook",
                "title": "校验工作簿",
                "description": "校验最终工作簿结构和输出结果。",
                "input_artifact": "formatted_workbook",
                "output_artifact": "validated_workbook",
                "params": {"final_target_sheet": "合并明细"},
                "validation": {"must_pass": True},
            }
        )
        next_id += 1
        steps.append(
            {
                "step_id": f"step_{next_id}",
                "step_type": "export_workbook",
                "title": "导出最终结果",
                "description": "导出最终 Excel 文件。",
                "input_artifact": "validated_workbook",
                "output_artifact": "final_workbook",
                "params": {"workbook_name": "complex_workflow_result.xlsx"},
                "validation": {"must_exist": True},
            }
        )
        return {
            "task_type": "complex_excel_workflow",
            "goal": message,
            "steps": steps,
            "requires_confirmation": any(step.get("requires_user_confirm") for step in steps),
            "assumptions": ["字段对齐优先使用轻度别名映射。"],
            "risks": ["复杂任务第一版不支持手动编辑字段映射。"],
        }


llm_service = LLMService()
