import json

from app.agent.state import AgentState
from app.services.llm_service import llm_service
from app.utils.jsonable import to_jsonable


def workbook_semantic_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    state.logs.append("Calling semantic model to understand workbook meaning.")
    try:
        semantics = llm_service.analyze_workbook_semantics(
            message=state.message,
            workbook_contexts=state.workbook_contexts,
            goal_understanding=state.goal_understanding,
        )
        state.workbook_semantics = to_jsonable(semantics)
        recommended_mode = semantics.get("recommended_task_mode")
        if recommended_mode in {"simple", "complex"}:
            state.task_mode = recommended_mode
        state.logs.append(
            "Workbook semantics: " + json.dumps(to_jsonable(semantics), ensure_ascii=False)
        )
    except Exception as exc:
        state.status = "failed"
        state.error = "Workbook semantic analysis failed."
        state.error_message = str(exc)
        state.technical_error = repr(exc)
        state.logs.append(f"Workbook semantic analysis failed: {exc}")
    return state
