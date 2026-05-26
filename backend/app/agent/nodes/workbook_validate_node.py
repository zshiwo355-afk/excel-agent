from app.agent.state import AgentState
from app.excel_tools.validator import validate_output_workbook
from app.schemas.excel_plan import ExcelPlan


def workbook_validate_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    if not state.output_file_path:
        raise ValueError("No output file generated.")

    plan = ExcelPlan.model_validate(state.excel_plan) if state.excel_plan else None
    validation = validate_output_workbook(state.output_file_path, plan, state.workbook_contexts)
    if not validation["ok"]:
        raise ValueError(validation["message"])

    state.logs.append("Generated workbook validation passed.")
    state.status = "completed"
    return state
