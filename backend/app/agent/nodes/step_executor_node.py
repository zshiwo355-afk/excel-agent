from app.agent.state import AgentState
from app.excel_tools.workflow_steps import execute_workflow_step
from app.schemas.task_plan import TaskPlan


def _mark_step(task_plan: TaskPlan, step_id: str, **updates) -> TaskPlan:
    for step in task_plan.steps:
        if step.step_id == step_id:
            for key, value in updates.items():
                setattr(step, key, value)
            break
    return task_plan


def step_executor_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    if not state.task_plan:
        raise ValueError("TaskPlan is required for complex workflow execution.")

    task_plan = TaskPlan.model_validate(state.task_plan)
    if state.current_step_index >= len(task_plan.steps):
        return state

    step = task_plan.steps[state.current_step_index]
    task_plan = _mark_step(task_plan, step.step_id, status="running", error=None)
    state.logs.append(f"Executing step {step.step_id}: {step.title}")
    result = execute_workflow_step(state, task_plan, step)

    if result.get("wait_for_confirm"):
        task_plan = _mark_step(
            task_plan,
            step.step_id,
            status="waiting_confirm",
            validation_result=result.get("result"),
        )
        state.task_plan = task_plan.model_dump(mode="json")
        state.pending_step_id = step.step_id
        state.last_executed_step_id = step.step_id
        state.last_step_result = result.get("result")
        state.status = "waiting_step_confirm"
        state.logs.append(f"Step {step.step_id} requires user confirmation.")
        return state

    artifact_path = result.get("artifact_path")
    if artifact_path and step.output_artifact:
        state.step_artifacts[step.output_artifact] = artifact_path
    task_plan = _mark_step(task_plan, step.step_id, status="completed")
    state.task_plan = task_plan.model_dump(mode="json")
    state.last_executed_step_id = step.step_id
    state.last_step_artifact = artifact_path
    state.last_step_result = result.get("result")
    if state.pending_step_id == step.step_id:
        state.pending_step_id = None
    state.logs.append(f"Step completed: {step.step_id}")
    return state
