from app.agent.state import AgentState


SUMMARY_OPERATIONS = {"merge", "summarize", "deduplicate", "aggregate", "compare"}
RESHAPE_OPERATIONS = {"split", "template", "reshape", "restructure", "layout"}
EDIT_OPERATIONS = {"edit", "delete", "insert", "sort", "clean", "format", "fill", "update"}

SUMMARY_KEYWORDS = {"合并", "汇总", "总表", "汇总表", "整合", "追加", "统计"}
SPLIT_KEYWORDS = {"拆分", "拆出", "子表", "每个", "一个表", "一个sheet", "一个 sheet"}
TEMPLATE_KEYWORDS = {"模板", "套模板", "按模板", "格式整理", "版式"}
RESHAPE_ENTITIES = {"公司", "门店", "药店", "部门", "客户", "企业"}


def _normalize_operations(goal_understanding: dict | None) -> set[str]:
    values = (goal_understanding or {}).get("requested_operations") or []
    return {str(item).strip().lower() for item in values if str(item).strip()}


def _message_route_hint(state: AgentState) -> str | None:
    message = state.message or ""
    lowered = message.lower()

    if any(keyword in message for keyword in TEMPLATE_KEYWORDS):
        return "reshape"

    if (
        any(keyword in message for keyword in SPLIT_KEYWORDS)
        and any(entity in message for entity in RESHAPE_ENTITIES)
    ):
        return "reshape"

    if "sheet" in lowered and "每" in message:
        return "reshape"

    if any(keyword in message for keyword in SUMMARY_KEYWORDS):
        return "summary"

    return None


def _pick_route(state: AgentState) -> str:
    goal_understanding = state.goal_understanding or {}
    workbook_semantics = state.workbook_semantics or {}
    operations = _normalize_operations(goal_understanding)
    route_hint = str(goal_understanding.get("task_route") or "").strip().lower()
    semantic_hint = str(workbook_semantics.get("recommended_task_route") or "").strip().lower()
    message_hint = _message_route_hint(state)

    # High-confidence message heuristics should override model drift for explicit split/template requests.
    if message_hint in {"edit", "summary", "reshape"}:
        return message_hint
    if operations & RESHAPE_OPERATIONS and not operations & SUMMARY_OPERATIONS:
        return "reshape"
    if operations & SUMMARY_OPERATIONS and not operations & RESHAPE_OPERATIONS:
        return "summary"
    if route_hint in {"edit", "summary", "reshape"}:
        return route_hint
    if semantic_hint in {"edit", "summary", "reshape"}:
        return semantic_hint
    if operations & EDIT_OPERATIONS:
        return "edit"
    if len(state.uploaded_file_paths or []) >= 2:
        return "summary"
    return "edit"


def _pick_task_mode(state: AgentState, route: str) -> str:
    operations = _normalize_operations(state.goal_understanding)
    file_count = len(state.uploaded_file_paths or [])

    if route == "reshape":
        # Current reshape capabilities are executed more reliably through ExcelPlan than TaskPlan.
        return "simple"

    if route == "summary":
        if file_count >= 2 or operations & SUMMARY_OPERATIONS:
            return "complex"
        return "simple"

    if file_count >= 2 and operations & {"compare"}:
        return "complex"
    if len(operations) >= 3:
        return "complex"
    return "simple"


def task_router_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    route = _pick_route(state)
    state.task_route = route
    state.task_mode = _pick_task_mode(state, route)
    state.logs.append(
        f"Task routed to '{state.task_route}' with {state.task_mode} execution mode."
    )
    return state
