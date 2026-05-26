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


def plan_validate_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    if state.status == "failed":
        return state
    if not state.excel_plan:
        state.status = "failed"
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
        elif plan.action == "create_workbook":
            if not plan.sheets:
                raise ValueError("ExcelPlan sheets cannot be empty.")
        elif plan.action == "merge_workbooks":
            _validate_merge_plan(state, plan)

        seen_names: set[str] = set()
        for sheet in plan.sheets:
            lowered = sheet.name.lower()
            if lowered in seen_names:
                raise ValueError(f"Duplicate sheet name detected: {sheet.name}")
            seen_names.add(lowered)

        state.excel_plan = plan.model_dump(mode="json")
        state.logs.append("ExcelPlan validation passed.")
        state.status = "waiting_confirm"
    except ValidationError as exc:
        missing_fields = [
            str(item["loc"][0])
            for item in exc.errors()
            if item.get("type") == "missing" and item.get("loc")
        ]
        state.status = "failed"
        state.error = "ExcelPlan 校验失败"
        state.error_message = summarize_excel_plan_validation_error(missing_fields)
        state.technical_error = str(exc)
        state.logs.append(f"ExcelPlan validation failed: {state.error_message}")
    except Exception as exc:
        state.status = "failed"
        state.error = "ExcelPlan 校验失败"
        state.error_message = str(exc)
        state.technical_error = repr(exc)
        state.logs.append(f"ExcelPlan validation failed: {exc}")
    return state
