import json

from app.agent.state import AgentState
from app.services.llm_service import llm_service
from app.utils.jsonable import to_jsonable


def goal_understanding_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    state.logs.append("Calling understanding model to extract the user goal.")
    try:
        understanding = llm_service.generate_goal_understanding(
            message=state.message,
            workbook_contexts=state.workbook_contexts,
        )
        state.goal_understanding = to_jsonable(understanding)
        task_mode = understanding.get("task_mode")
        if task_mode in {"simple", "complex"}:
            state.task_mode = task_mode
        state.logs.append(
            "Goal understanding: " + json.dumps(to_jsonable(understanding), ensure_ascii=False)
        )
    except Exception as exc:
        state.status = "failed"
        state.error = "Goal understanding failed."
        state.error_message = str(exc)
        state.technical_error = repr(exc)
        state.logs.append(f"Goal understanding failed: {exc}")
    return state
