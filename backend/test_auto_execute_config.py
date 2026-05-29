from app.config import Settings
from app.schemas.execution_step import ExecutionStep
from app.schemas.task import TaskDetail
from app.services.task_service import TaskService


def run_auto_execute_config_test() -> None:
    settings = Settings(EXCEL_AGENT_AUTO_EXECUTE=True, EXCEL_AGENT_STEP_DEBUG_DELAY_MS=600)
    assert settings.auto_execute_default is True
    assert settings.excel_agent_step_debug_delay_ms == 600

    task = TaskDetail(
        task_id="auto-execute-test",
        message="test",
        status="planning",
        auto_execute=True,
        execution_steps=[
            ExecutionStep(
                step_id="step_1",
                title="识别日期列",
                status="pending",
                detail="Sheet1",
            )
        ],
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    service = TaskService()
    payload = service.save_task(task)
    assert payload.auto_execute is True


if __name__ == "__main__":
    run_auto_execute_config_test()
    print("auto execute config test passed")
