from app.agent.state import AgentState


def execution_router_node(state: AgentState) -> AgentState:
    return AgentState.model_validate(state)
