from app.agent.state import AgentState
from app.excel_tools.profiler import profile_workbook


def file_analyze_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    if state.uploaded_file_path:
        state.logs.append("File analysis started.")
        state.workbook_context = profile_workbook(state.uploaded_file_path)
        state.logs.append("File analysis completed.")
        state.logs.append(
            "Detected sheets: " + ", ".join(state.workbook_context.get("sheet_names", []))
        )
        for sheet in state.workbook_context.get("sheets", []):
            state.logs.append(f"Detected header row: {sheet.get('header_row')}")
            state.logs.append(f"Detected data start row: {sheet.get('data_start_row')}")
    else:
        state.workbook_context = None
        state.logs.append("No upload provided. Planning a new workbook.")
    return state
