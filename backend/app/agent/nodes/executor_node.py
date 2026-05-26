from pathlib import Path

from app.agent.state import AgentState
from app.config import get_settings
from app.excel_tools.builder import create_workbook_from_plan
from app.excel_tools.modifier import modify_workbook_from_plan
from app.excel_tools.validator import validate_output_workbook
from app.schemas.excel_plan import ExcelPlan


def executor_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    settings = get_settings()
    plan = ExcelPlan.model_validate(state.excel_plan)
    output_dir = settings.outputs_dir / state.task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{Path(plan.workbook_name).stem}.xlsx"

    state.logs.append("Executing ExcelPlan.")
    if state.workbook_context and any(
        sheet.get("merged_cells") for sheet in state.workbook_context.get("sheets", [])
    ):
        state.logs.append("Detected merged cells, safe formatting mode enabled.")
    for sheet_plan in plan.sheets:
        target_name = sheet_plan.source_sheet or sheet_plan.name
        if sheet_plan.header_row:
            state.logs.append(f"Detected header row: {sheet_plan.header_row}")
        if sheet_plan.data_start_row:
            state.logs.append(f"Detected data start row: {sheet_plan.data_start_row}")
        if sheet_plan.style:
            state.logs.append(f"Applying style to sheet: {target_name}")
        if sheet_plan.sort:
            state.logs.append(
                f"Sorting sheet {target_name} by column {sheet_plan.sort.column} {sheet_plan.sort.order}"
            )
    if plan.action == "create_workbook":
        create_workbook_from_plan(plan, output_path)
    else:
        if not state.uploaded_file_path:
            raise ValueError("Uploaded workbook is required for modify_workbook.")
        modify_workbook_from_plan(plan, Path(state.uploaded_file_path), output_path)

    if any(sheet_plan.sort for sheet_plan in plan.sheets):
        state.logs.append("Sort completed")

    validation = validate_output_workbook(output_path, plan)
    state.logs.append("Workbook validation completed")
    if not validation["ok"]:
        raise ValueError(validation["message"])

    state.output_file_path = str(output_path)
    state.logs.append(f"Workbook written to {output_path}.")
    return state
