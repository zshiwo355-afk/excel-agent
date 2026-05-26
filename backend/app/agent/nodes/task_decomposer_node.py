from pydantic import ValidationError

from app.agent.state import AgentState
from app.schemas.task_plan import TaskPlan
from app.services.llm_service import llm_service


def task_decomposer_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    state.logs.append("Calling planner model to generate TaskPlan.")
    try:
        task_plan = llm_service.generate_task_plan(
            message=state.message,
            workbook_contexts=state.workbook_contexts,
        )
        plan = TaskPlan.model_validate(task_plan)
        if len(plan.steps) < 2:
            raise ValueError("复杂任务必须拆成多个 StepPlan。")
        if not any(step.step_type == "merge_workbooks" for step in plan.steps):
            state.logs.append("TaskPlan does not include merge_workbooks step.")
        state.task_plan = plan.model_dump(mode="json")
        state.logs.append("TaskPlan generated successfully.")
        state.status = "waiting_confirm"
    except ValidationError as exc:
        state.status = "failed"
        state.error = "TaskPlan 校验失败"
        state.error_message = "复杂任务拆解失败，返回的 TaskPlan 结构不合法。"
        state.technical_error = str(exc)
        state.logs.append(f"TaskPlan validation failed: {exc}")
    except Exception as exc:
        state.status = "failed"
        state.error = "TaskPlan 生成失败"
        state.error_message = str(exc)
        state.technical_error = repr(exc)
        state.logs.append(f"TaskPlan generation failed: {exc}")
    return state
