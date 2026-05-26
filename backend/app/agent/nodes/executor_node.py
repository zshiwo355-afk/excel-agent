from pathlib import Path

from app.agent.state import AgentState
from app.config import get_settings
from app.excel_tools.builder import create_workbook_from_plan
from app.excel_tools.merger import merge_workbooks_by_plan
from app.excel_tools.modifier import modify_workbook_from_plan
from app.excel_tools.splitter import split_workbook_by_column
from app.excel_tools.validator import validate_output_workbook
from app.schemas.excel_plan import ExcelPlan


def executor_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    settings = get_settings()
    plan = ExcelPlan.model_validate(state.excel_plan)
    output_dir = settings.outputs_dir / state.task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{Path(plan.workbook_name).stem}.xlsx"

    if plan.action == "merge_workbooks":
        state.logs.append("Executing merge_workbooks.")
        for source_sheet in plan.merge.source_sheets if plan.merge else []:
            state.logs.append(f"Merging sheet {source_sheet.file_name} / {source_sheet.sheet_name}")
        merge_workbooks_by_plan(plan, state.workbook_contexts, output_path)
    else:
        state.logs.append("Executing ExcelPlan.")
        split_sheet_plan = next((sheet for sheet in plan.sheets if sheet.operation == "split_sheet_by_column"), None)
        if split_sheet_plan:
            state.logs.append(
                f"Splitting sheet {split_sheet_plan.source_sheet} by column {split_sheet_plan.split.column}"
            )
            if not state.uploaded_file_path:
                raise ValueError("Uploaded workbook is required for split_sheet_by_column.")
            split_result = split_workbook_by_column(plan, Path(state.uploaded_file_path), output_path)
            for sheet_name in split_result["created_sheet_names"]:
                state.logs.append(f"Created sheet for value: {sheet_name}")
            state.logs.append(f"Created split sheets: {split_result['total_split_sheets']}")
        else:
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

    validation = validate_output_workbook(output_path, plan, state.workbook_contexts)
    if plan.action == "merge_workbooks":
        state.logs.append(f"Expected merged rows: {validation.get('expected_rows', 0)}")
        state.logs.append(f"Actual merged rows: {validation.get('actual_rows', 0)}")
        state.logs.append("Merge validation completed")
    else:
        state.logs.append("Workbook validation completed")
    if not validation["ok"]:
        raise ValueError(validation["message"])

    state.output_file_path = str(output_path)
    state.logs.append(f"Workbook written to {output_path}.")
    return state
