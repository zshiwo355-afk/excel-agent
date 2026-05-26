from app.agent.state import AgentState
from app.excel_tools.profiler import profile_workbook


def file_analyze_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    upload_items = state.uploaded_files or []
    upload_paths = state.uploaded_file_paths or ([state.uploaded_file_path] if state.uploaded_file_path else [])

    if upload_paths:
        state.logs.append("File analysis started.")
        workbook_contexts: list[dict] = []
        for index, file_path in enumerate(upload_paths, start=1):
            upload_item = upload_items[index - 1] if index - 1 < len(upload_items) else {}
            file_name = upload_item.get("file_name") or file_path.split("\\")[-1].split("/")[-1]
            file_id = upload_item.get("file_id") or f"file_{index}"
            state.logs.append(f"Analyzing workbook: {file_name}")
            workbook_context = profile_workbook(
                file_path,
                file_id=file_id,
                file_name=file_name,
            )
            workbook_contexts.append(workbook_context)
            state.logs.append(
                f"Detected sheets in {file_name}: " + ", ".join(workbook_context.get("sheet_names", []))
            )

        state.workbook_contexts = workbook_contexts
        state.workbook_context = workbook_contexts[0] if workbook_contexts else None
        state.logs.append(f"File analysis completed. Total workbooks: {len(workbook_contexts)}")
    else:
        state.workbook_context = None
        state.workbook_contexts = []
        state.logs.append("No upload provided. Planning a new workbook.")
    return state
