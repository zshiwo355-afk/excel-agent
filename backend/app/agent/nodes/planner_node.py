import json

from app.agent.state import AgentState
from app.config import get_settings
from app.services.llm_service import llm_service
from app.utils.jsonable import to_jsonable


def planner_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    settings = get_settings()
    state.logs.append("Calling planner model to generate ExcelPlan.")
    if settings.use_mock_llm or not settings.deepseek_api_key:
        state.logs.append("当前未配置真实 LLM，正在使用 mock planner。")
    try:
        plan, raw_response = llm_service.generate_excel_plan(
            message=state.message,
            workbook_context=state.workbook_context,
            workbook_contexts=state.workbook_contexts,
            uploaded_file_path=state.uploaded_file_path,
            uploaded_file_paths=state.uploaded_file_paths,
        )
        state.raw_llm_response = to_jsonable(raw_response)
        state.logs.append(
            "Raw LLM response: " + json.dumps(to_jsonable(raw_response), ensure_ascii=False)
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
