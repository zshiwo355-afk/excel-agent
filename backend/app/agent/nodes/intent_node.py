from app.agent.state import AgentState


def intent_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    state.logs.append("Intent node is reserved for future intent classification.")
    return state
