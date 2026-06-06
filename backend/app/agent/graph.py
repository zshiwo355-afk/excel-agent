from langgraph.graph import END, StateGraph

from app.agent.nodes.executor_node import executor_node
from app.agent.nodes.execution_router_node import execution_router_node
from app.agent.nodes.file_analyze_node import file_analyze_node
from app.agent.nodes.goal_understanding_node import goal_understanding_node
from app.agent.nodes.plan_validate_node import plan_validate_node
from app.agent.nodes.planner_node import planner_node
from app.agent.nodes.step_executor_node import step_executor_node
from app.agent.nodes.step_validator_node import step_validator_node
from app.agent.nodes.task_router_node import task_router_node
from app.agent.nodes.task_decomposer_node import task_decomposer_node
from app.agent.nodes.workbook_semantic_node import workbook_semantic_node
from app.agent.nodes.workbook_validate_node import workbook_validate_node
from app.agent.state import AgentState


def _route_after_intent(state: AgentState) -> str:
    return "complex" if state.task_mode == "complex" else "simple"


def _route_after_step_validation(state: AgentState) -> str:
    if state.status in {"completed", "failed", "waiting_step_confirm"}:
        return state.status
    return "continue"


def _route_execution(state: AgentState) -> str:
    return "complex" if state.task_mode == "complex" else "simple"


def build_plan_graph():
    graph = StateGraph(AgentState)
    graph.add_node("file_analyze_node", file_analyze_node)
    graph.add_node("goal_understanding_node", goal_understanding_node)
    graph.add_node("workbook_semantic_node", workbook_semantic_node)
    graph.add_node("task_router_node", task_router_node)
    graph.add_node("planner_node", planner_node)
    graph.add_node("plan_validate_node", plan_validate_node)
    graph.add_node("task_decomposer_node", task_decomposer_node)

    graph.set_entry_point("file_analyze_node")
    graph.add_edge("file_analyze_node", "goal_understanding_node")
    graph.add_edge("goal_understanding_node", "workbook_semantic_node")
    graph.add_edge("workbook_semantic_node", "task_router_node")
    graph.add_conditional_edges(
        "task_router_node",
        _route_after_intent,
        {
            "simple": "planner_node",
            "complex": "task_decomposer_node",
        },
    )
    graph.add_edge("planner_node", "plan_validate_node")
    graph.add_edge("plan_validate_node", END)
    graph.add_edge("task_decomposer_node", END)
    return graph.compile()


def build_execute_graph():
    graph = StateGraph(AgentState)
    graph.add_node("execution_router_node", execution_router_node)
    graph.add_node("executor_node", executor_node)
    graph.add_node("workbook_validate_node", workbook_validate_node)
    graph.add_node("step_executor_node", step_executor_node)
    graph.add_node("step_validator_node", step_validator_node)

    graph.set_entry_point("execution_router_node")
    graph.add_conditional_edges(
        "execution_router_node",
        _route_execution,
        {
            "simple": "executor_node",
            "complex": "step_executor_node",
        },
    )
    graph.add_edge("executor_node", "workbook_validate_node")
    graph.add_edge("workbook_validate_node", END)
    graph.add_edge("step_executor_node", "step_validator_node")
    graph.add_conditional_edges(
        "step_validator_node",
        _route_after_step_validation,
        {
            "continue": "step_executor_node",
            "waiting_step_confirm": END,
            "completed": END,
            "failed": END,
        },
    )
    return graph.compile()


plan_graph = build_plan_graph()
execute_graph = build_execute_graph()
