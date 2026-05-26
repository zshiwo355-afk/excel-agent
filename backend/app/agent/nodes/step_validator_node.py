from app.agent.state import AgentState
from app.excel_tools.workflow_steps import validate_workflow_step
from app.schemas.task_plan import TaskPlan


def _update_step(task_plan: TaskPlan, step_id: str, **updates) -> TaskPlan:
    for step in task_plan.steps:
        if step.step_id == step_id:
            for key, value in updates.items():
                setattr(step, key, value)
            break
    return task_plan


def step_validator_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    if state.status == "waiting_step_confirm":
        return state
    if not state.task_plan or not state.last_executed_step_id:
        return state

    task_plan = TaskPlan.model_validate(state.task_plan)
    step = next((item for item in task_plan.steps if item.step_id == state.last_executed_step_id), None)
    if step is None:
        return state

    validation = validate_workflow_step(state, task_plan, step)
    task_plan = _update_step(task_plan, step.step_id, validation_result=validation)
    state.task_plan = task_plan.model_dump(mode="json")
    state.logs.append(f"Step validation: {step.step_id} -> {validation['message']}")

    if not validation["ok"]:
        task_plan = _update_step(task_plan, step.step_id, status="failed", error=validation["message"])
        state.task_plan = task_plan.model_dump(mode="json")
        state.status = "failed"
        state.error = "复杂任务步骤校验失败"
        state.error_message = validation["message"]
        return state

    state.current_step_index += 1
    if step.output_artifact == "final_workbook" and state.last_step_artifact:
        state.output_file_path = state.last_step_artifact

    if state.current_step_index >= len(task_plan.steps):
        state.status = "completed"
        if state.last_step_artifact and not state.output_file_path:
            state.output_file_path = state.last_step_artifact
        state.logs.append("Complex workflow completed.")
    else:
        state.status = "running"
    return state
