from pydantic import ValidationError

from app.agent.state import AgentState
from app.schemas.excel_plan import ExcelPlan, summarize_excel_plan_validation_error


def plan_validate_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    if state.status == "failed":
        return state
    if not state.excel_plan:
        state.status = "failed"
        state.error = "ExcelPlan 校验失败。"
        state.error_message = "Planner 未返回可执行的 ExcelPlan。"
        state.technical_error = "Planner returned empty excel_plan."
        state.logs.append("ExcelPlan validation failed: planner returned empty plan.")
        return state

    try:
        plan = ExcelPlan.model_validate(state.excel_plan)

        if plan.action not in {"create_workbook", "modify_workbook"}:
            raise ValueError("ExcelPlan action must be create_workbook or modify_workbook.")
        if not plan.workbook_name.strip():
            raise ValueError("ExcelPlan workbook_name cannot be empty.")
        if not plan.sheets:
            raise ValueError("ExcelPlan sheets cannot be empty.")

        seen_names: set[str] = set()
        for sheet in plan.sheets:
            if not sheet.name.strip():
                raise ValueError("Sheet name cannot be empty.")
            if len(sheet.name) > 31:
                raise ValueError(f"Sheet name '{sheet.name}' exceeds 31 characters.")
            if sheet.operation in {"sort_rows", "format_and_sort_sheet"} and not sheet.sort:
                raise ValueError(f"Sheet '{sheet.name}' sort operation requires sort configuration.")
            if sheet.operation == "clean_sheet" and not sheet.clean:
                raise ValueError(f"Sheet '{sheet.name}' clean operation requires clean configuration.")
            lowered = sheet.name.lower()
            if lowered in seen_names:
                raise ValueError(f"Duplicate sheet name detected: {sheet.name}")
            seen_names.add(lowered)

        if plan.action == "modify_workbook" and not state.uploaded_file_path:
            raise ValueError("modify_workbook requires an uploaded_file_path.")

        state.excel_plan = plan.model_dump(mode="json")
        state.logs.append("ExcelPlan validation passed.")
        state.status = "waiting_confirm"
    except ValidationError as exc:
        missing_fields = [
            item["loc"][0]
            for item in exc.errors()
            if item.get("type") == "missing" and item.get("loc")
        ]
        state.status = "failed"
        state.error = "ExcelPlan 校验失败。"
        state.error_message = summarize_excel_plan_validation_error(missing_fields)
        state.technical_error = str(exc)
        state.logs.append(f"ExcelPlan validation failed: {state.error_message}")
    except Exception as exc:
        state.status = "failed"
        state.error = "ExcelPlan 校验失败。"
        state.error_message = f"ExcelPlan 校验失败：{exc}"
        state.technical_error = repr(exc)
        state.logs.append(f"ExcelPlan validation failed: {exc}")
    return state
