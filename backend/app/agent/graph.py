from langgraph.graph import END, StateGraph

from app.agent.nodes.executor_node import executor_node
from app.agent.nodes.file_analyze_node import file_analyze_node
from app.agent.nodes.plan_validate_node import plan_validate_node
from app.agent.nodes.planner_node import planner_node
from app.agent.nodes.workbook_validate_node import workbook_validate_node
from app.agent.state import AgentState


def build_plan_graph():
    graph = StateGraph(AgentState)
    graph.add_node("file_analyze_node", file_analyze_node)
    graph.add_node("planner_node", planner_node)
    graph.add_node("plan_validate_node", plan_validate_node)

    graph.set_entry_point("file_analyze_node")
    graph.add_edge("file_analyze_node", "planner_node")
    graph.add_edge("planner_node", "plan_validate_node")
    graph.add_edge("plan_validate_node", END)
    return graph.compile()


def build_execute_graph():
    graph = StateGraph(AgentState)
    graph.add_node("executor_node", executor_node)
    graph.add_node("workbook_validate_node", workbook_validate_node)

    graph.set_entry_point("executor_node")
    graph.add_edge("executor_node", "workbook_validate_node")
    graph.add_edge("workbook_validate_node", END)
    return graph.compile()


plan_graph = build_plan_graph()
execute_graph = build_execute_graph()
