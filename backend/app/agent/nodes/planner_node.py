import json

from app.agent.state import AgentState
from app.services.llm_service import llm_service


def planner_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    state.logs.append("Calling planner model to generate ExcelPlan.")
    try:
        plan, raw_response = llm_service.generate_excel_plan(
            message=state.message,
            workbook_context=state.workbook_context,
            workbook_contexts=state.workbook_contexts,
            uploaded_file_path=state.uploaded_file_path,
            uploaded_file_paths=state.uploaded_file_paths,
        )
        state.raw_llm_response = raw_response
        state.logs.append(
            "Raw LLM response: " + json.dumps(raw_response, ensure_ascii=False)
        )
        state.excel_plan = plan
        state.logs.append("Planner returned normalized ExcelPlan JSON.")
    except Exception as exc:
        state.status = "failed"
        state.error = "ExcelPlan 生成失败。"
        state.error_message = str(exc)
        state.technical_error = repr(exc)
        state.logs.append(f"Planner failed: {exc}")
    return state
