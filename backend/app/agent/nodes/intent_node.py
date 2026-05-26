from app.agent.state import AgentState


COMPLEX_KEYWORDS = [
    "\u53bb\u91cd",
    "\u6c47\u603b",
    "\u56fe\u8868",
    "\u5f02\u5e38\u6570\u636e",
    "\u5b57\u6bb5\u5bf9\u9f50",
    "\u5b57\u6bb5\u6620\u5c04",
    "\u591a\u4e2a\u8f93\u51fa",
]
ACTION_KEYWORDS = [
    "\u5408\u5e76",
    "\u6e05\u6d17",
    "\u53bb\u91cd",
    "\u6c47\u603b",
    "\u56fe\u8868",
    "\u5f02\u5e38",
    "\u6392\u5e8f",
    "\u683c\u5f0f\u5316",
]


def _is_complex_message(message: str) -> bool:
    action_hits = sum(1 for keyword in ACTION_KEYWORDS if keyword in message)
    if action_hits >= 2:
        return True
    if any(keyword in message for keyword in COMPLEX_KEYWORDS):
        return True
    if all(token in message for token in ["\u5148", "\u518d", "\u6700\u540e"]):
        return True
    lowered = message.lower()
    if "sheet" in lowered and ("\u591a\u4e2a" in message or "\u8f93\u51fa" in message):
        return True
    return False


def intent_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    has_multi_files = len(state.uploaded_file_paths or []) >= 2
    is_complex = _is_complex_message(state.message)
    lowered = state.message.lower()
    if has_multi_files and "sheet" in lowered:
        is_complex = True
    if has_multi_files and any(
        keyword in state.message
        for keyword in [
            "\u5b57\u6bb5\u5bf9\u9f50",
            "\u6c47\u603b",
            "\u5f02\u5e38\u6570\u636e",
            "\u53bb\u91cd",
        ]
    ):
        is_complex = True

    state.task_mode = "complex" if is_complex else "simple"
    state.logs.append(f"Task complexity classified as {state.task_mode}.")
    return state
