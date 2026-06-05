from pydantic import ValidationError

from app.agent.state import AgentState
from app.schemas.excel_plan import ExcelPlan, summarize_excel_plan_validation_error


SPLIT_COLUMN_ALIASES = [
    "公司",
    "公司名称",
    "企业",
    "企业名称",
    "客户公司",
    "客户",
    "销售客户",
    "单位",
    "药店",
    "门店",
    "部门",
    "部门名称",
]
def _build_sheet_index(workbook_contexts: list[dict]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for workbook in workbook_contexts:
        file_id = workbook.get("file_id")
        for sheet in workbook.get("sheets", []):
            pairs.add((file_id, sheet.get("name")))
    return pairs


def _find_sheet_context(state: AgentState, source_sheet: str) -> dict | None:
    if state.workbook_context:
        for sheet in state.workbook_context.get("sheets", []):
            if sheet.get("name") == source_sheet:
                return sheet
    return None


def _validate_merge_plan(state: AgentState, plan: ExcelPlan) -> None:
    if not plan.merge:
        raise ValueError("合并计划缺少 source_sheets")
    if plan.merge.mode != "append_rows":
        raise ValueError("第一版只支持 append_rows 合并")
    if len(state.uploaded_file_paths or []) < 2:
        raise ValueError("合并至少需要两个 Excel 文件")
    if len(plan.merge.source_sheets) < 2:
        raise ValueError("合并计划缺少 source_sheets")

    existing_pairs = _build_sheet_index(state.workbook_contexts)
    for source_sheet in plan.merge.source_sheets:
        if source_sheet.header_row <= 0 or source_sheet.data_start_row <= 0:
            raise ValueError("header_row 和 data_start_row 必须为正整数")
        if (source_sheet.file_id, source_sheet.sheet_name) not in existing_pairs:
            raise ValueError("source_sheet 在上传文件中不存在")


def _validate_split_sheet_plan(state: AgentState, plan: ExcelPlan) -> None:
    for sheet_plan in plan.sheets:
        if sheet_plan.operation != "split_sheet_by_column":
            continue
        if not sheet_plan.split or not sheet_plan.split.column:
            raise ValueError("split_sheet_by_column 缺少 split.column")
        if not sheet_plan.source_sheet:
            raise ValueError("split_sheet_by_column 缺少 source_sheet")
        sheet_context = _find_sheet_context(state, sheet_plan.source_sheet)
        if not sheet_context:
            raise ValueError("source_sheet 在上传文件中不存在")

        headers = sheet_context.get("headers", [])
        split_column = sheet_plan.split.column
        if split_column in headers:
            continue

        matched = False
        for header in headers:
            if any(alias == split_column or alias in header for alias in SPLIT_COLUMN_ALIASES):
                matched = True
                break
        if not matched:
            raise ValueError("未找到用于拆分的字段，请确认表头中是否包含公司/客户/销售客户/门店等字段。")


def _find_sheet_context_in_workbooks(state: AgentState, file_id: str, sheet_name: str) -> dict | None:
    for workbook in state.workbook_contexts:
        if workbook.get("file_id") != file_id:
            continue
        for sheet in workbook.get("sheets", []):
            if sheet.get("name") == sheet_name:
                return sheet
    return None


def _validate_template_sheet_plan(state: AgentState, plan: ExcelPlan) -> None:
    for sheet_plan in plan.sheets:
        if sheet_plan.operation != "apply_template_sheet":
            continue
        if not sheet_plan.template:
            raise ValueError("apply_template_sheet 缺少 template 配置。")
        template = sheet_plan.template
        source_sheet_name = template.source_sheet or sheet_plan.source_sheet
        if not source_sheet_name:
            raise ValueError("apply_template_sheet 缺少 source_sheet。")
        source_context = _find_sheet_context_in_workbooks(
            state,
            template.source_file_id or "file_1",
            source_sheet_name,
        )
        if not source_context:
            raise ValueError("模板整理的数据源 sheet 不存在。")
        template_context = _find_sheet_context_in_workbooks(
            state,
            template.template_file_id,
            template.template_sheet,
        )
        if not template_context:
            raise ValueError("模板整理的模板 sheet 不存在。")
        if sheet_plan.sort:
            source_headers = source_context.get("headers", [])
            if sheet_plan.sort.column not in source_headers and sheet_plan.sort.column not in (template.column_mapping or {}):
                raise ValueError("模板整理计划中的排序字段不存在。")


def _validate_sort_plan(state: AgentState, plan: ExcelPlan) -> None:
    for sheet_plan in plan.sheets:
        if sheet_plan.operation not in {"sort_rows", "format_and_sort_sheet", "apply_template_sheet"}:
            continue
        if not sheet_plan.sort:
            raise ValueError("排序任务缺少排序列，请指定按哪一列排序。")
        if not sheet_plan.sort.column or not sheet_plan.sort.order:
            raise ValueError("排序任务缺少排序列或排序方向，请补充排序要求。")
        source_sheet_name = sheet_plan.source_sheet or sheet_plan.name
        if sheet_plan.operation == "apply_template_sheet":
            continue
        sheet_context = _find_sheet_context(state, source_sheet_name)
        if sheet_context:
            source_headers = sheet_context.get("headers", [])
            if sheet_plan.sort.column not in source_headers:
                raise ValueError(f"未找到排序列 '{sheet_plan.sort.column}'，请确认表头名称。")


def plan_validate_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    if state.status == "failed":
        return state
    if not state.excel_plan:
        state.status = "failed"
        state.status_message = "思考失败"
        state.error = "ExcelPlan 校验失败"
        state.error_message = "Planner 未返回可执行的 ExcelPlan。"
        state.technical_error = "Planner returned empty excel_plan."
        state.logs.append("ExcelPlan validation failed: planner returned empty plan.")
        return state

    try:
        plan = ExcelPlan.model_validate(state.excel_plan)
        if plan.action == "modify_workbook":
            if not state.uploaded_file_path:
                raise ValueError("modify_workbook requires an uploaded_file_path.")
            if not plan.sheets:
                raise ValueError("ExcelPlan sheets cannot be empty.")
            _validate_split_sheet_plan(state, plan)
            _validate_template_sheet_plan(state, plan)
            _validate_sort_plan(state, plan)
        elif plan.action == "create_workbook":
            if not plan.sheets:
                raise ValueError("ExcelPlan sheets cannot be empty.")
        elif plan.action == "merge_workbooks":
            _validate_merge_plan(state, plan)

        if plan.action != "modify_workbook":
            seen_names: set[str] = set()
            for sheet in plan.sheets:
                lowered = sheet.name.lower()
                if lowered in seen_names:
                    raise ValueError(f"Duplicate sheet name detected: {sheet.name}")
                seen_names.add(lowered)

        state.excel_plan = plan.model_dump(mode="json")
        state.logs.append("ExcelPlan validation passed.")
        state.status = "waiting_confirm"
        state.status_message = "思考完成"
    except ValidationError as exc:
        missing_fields = [
            str(item["loc"][0])
            for item in exc.errors()
            if item.get("type") == "missing" and item.get("loc")
        ]
        error_message = summarize_excel_plan_validation_error(missing_fields)
        state.status = "failed"
        state.status_message = "思考失败"
        state.error = "ExcelPlan 校验失败"
        state.error_message = error_message
        state.technical_error = str(exc)
        state.logs.append(f"ExcelPlan validation failed: {state.error_message}")
    except Exception as exc:
        error_message = str(exc)
        state.status = "failed"
        state.status_message = "思考失败"
        state.error = "ExcelPlan 校验失败"
        state.error_message = error_message
        state.technical_error = repr(exc)
        state.logs.append(f"ExcelPlan validation failed: {exc}")
    return state
