import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.agent.graph import execute_graph, plan_graph
from app.agent.state import AgentState
from app.config import get_settings
from app.services.file_service import file_service
from app.schemas.task import TaskDetail


class TaskService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _task_path(self, task_id: str) -> Path:
        return self.settings.tasks_dir / f"{task_id}.json"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_task(self, task: TaskDetail) -> TaskDetail:
        path = self._task_path(task.task_id)
        path.write_text(
            json.dumps(task.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return task

    def get_task(self, task_id: str) -> TaskDetail:
        path = self._task_path(task_id)
        if not path.exists():
            raise FileNotFoundError(f"Task not found: {task_id}")
        return TaskDetail.model_validate_json(path.read_text(encoding="utf-8"))

    def list_tasks(self) -> list[TaskDetail]:
        tasks: list[TaskDetail] = []
        for path in sorted(self.settings.tasks_dir.glob("*.json"), reverse=True):
            try:
                tasks.append(TaskDetail.model_validate_json(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return sorted(tasks, key=lambda item: item.created_at, reverse=True)

    def resolve_existing_file(self, file_path: str) -> Path:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return path

    async def create_task(self, message: str, upload: UploadFile | None) -> TaskDetail:
        if not message.strip():
            raise ValueError("message cannot be empty.")

        task_id = uuid4().hex
        uploaded_file_path: str | None = None
        logs = ["Task created."]

        if upload:
            uploaded_path = await file_service.save_upload(task_id, upload)
            uploaded_file_path = str(uploaded_path)
            logs.append(f"Upload saved to {uploaded_path}.")

        task = TaskDetail(
            task_id=task_id,
            message=message,
            status="planning",
            uploaded_file_path=uploaded_file_path,
            created_at=self._now(),
            updated_at=self._now(),
            logs=logs,
        )
        self.save_task(task)

        try:
            state = AgentState(
                task_id=task.task_id,
                message=task.message,
                uploaded_file_path=task.uploaded_file_path,
                logs=task.logs.copy(),
                status=task.status,
            )
            result = AgentState.model_validate(plan_graph.invoke(state))
            task.status = result.status
            task.workbook_context = result.workbook_context
            task.excel_plan = result.excel_plan
            task.raw_llm_response = result.raw_llm_response
            task.logs = result.logs
            task.error = result.error
            task.error_message = result.error_message
            task.technical_error = result.technical_error
        except Exception as exc:
            task.status = "failed"
            task.error = "任务执行失败。"
            task.error_message = "任务执行失败，请检查执行日志。"
            task.technical_error = traceback.format_exc()
            task.logs.append(traceback.format_exc())

        task.updated_at = self._now()
        return self.save_task(task)

    def confirm_task(self, task_id: str) -> TaskDetail:
        task = self.get_task(task_id)
        if task.status != "waiting_confirm":
            raise ValueError("Task status must be waiting_confirm before execution.")
        if not task.excel_plan:
            raise ValueError("Task has no ExcelPlan to execute.")

        task.status = "running"
        task.updated_at = self._now()
        self.save_task(task)

        try:
            state = AgentState(
                task_id=task.task_id,
                message=task.message,
                uploaded_file_path=task.uploaded_file_path,
                workbook_context=task.workbook_context,
                excel_plan=task.excel_plan,
                logs=task.logs.copy(),
                status=task.status,
            )
            result = AgentState.model_validate(execute_graph.invoke(state))
            task.status = result.status
            task.output_file_path = result.output_file_path
            task.logs = result.logs
            task.error = None
            task.error_message = None
            task.technical_error = None
        except Exception as exc:
            task.status = "failed"
            task.error = "Excel 生成失败。"
            task.error_message = f"Excel 生成失败：{exc}"
            task.technical_error = traceback.format_exc()
            task.logs.append(traceback.format_exc())

        task.updated_at = self._now()
        return self.save_task(task)


task_service = TaskService()
