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
from app.schemas.execution_step import ExecutionStep
from app.schemas.task import TaskDetail
from app.utils.jsonable import to_jsonable


class TaskService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _task_path(self, task_id: str) -> Path:
        return self.settings.tasks_dir / f"{task_id}.json"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_task(self, task: TaskDetail) -> TaskDetail:
        path = self._task_path(task.task_id)
        payload = to_jsonable(task.model_dump(mode="python"))
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return task

    def save_runtime_state(self, state: AgentState) -> None:
        try:
            task = self.get_task(state.task_id)
        except FileNotFoundError:
            return

        task.status = state.status
        task.output_file_path = state.output_file_path
        task.workbook_context = state.workbook_context
        task.workbook_contexts = state.workbook_contexts
        task.excel_plan = state.excel_plan
        task.task_plan = state.task_plan
        task.task_mode = state.task_mode
        task.step_artifacts = state.step_artifacts
        task.current_step_index = state.current_step_index
        task.confirmed_step_ids = state.confirmed_step_ids
        task.pending_step_id = state.pending_step_id
        task.error = state.error
        task.error_message = state.error_message
        task.technical_error = state.technical_error
        task.raw_llm_response = state.raw_llm_response
        task.execution_steps = [
            step if isinstance(step, ExecutionStep) else ExecutionStep.model_validate(step)
            for step in state.execution_steps
        ]
        task.logs = state.logs
        task.updated_at = self._now()
        self.save_task(task)

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

    async def create_task(
        self,
        message: str,
        upload: UploadFile | None,
        uploads: list[UploadFile] | None = None,
        auto_execute: bool | None = None,
    ) -> TaskDetail:
        if not message.strip():
            raise ValueError("message cannot be empty.")

        task_id = uuid4().hex
        uploaded_file_path: str | None = None
        uploaded_files: list[dict] = []
        uploaded_file_paths: list[str] = []
        logs = ["Task created."]

        pending_uploads = [item for item in (uploads or []) if item and item.filename]
        if upload and upload.filename:
            pending_uploads = [upload, *pending_uploads]

        if pending_uploads:
            uploaded_files = await file_service.save_uploads(task_id, pending_uploads)
            uploaded_file_paths = [item["file_path"] for item in uploaded_files]
            uploaded_file_path = uploaded_file_paths[0] if uploaded_file_paths else None
            for item in uploaded_files:
                logs.append(f"Upload saved: {item['file_name']}")

        task = TaskDetail(
            task_id=task_id,
            message=message,
            status="planning",
            auto_execute=self.settings.auto_execute_default if auto_execute is None else auto_execute,
            uploaded_file_path=uploaded_file_path,
            uploaded_file_paths=uploaded_file_paths,
            uploaded_files=uploaded_files,
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
                uploaded_file_paths=task.uploaded_file_paths,
                uploaded_files=[item.model_dump(mode="json") for item in task.uploaded_files],
                logs=task.logs.copy(),
                status=task.status,
            )
            result = AgentState.model_validate(plan_graph.invoke(state))
            task.status = result.status
            task.task_mode = result.task_mode
            task.workbook_context = result.workbook_context
            task.workbook_contexts = result.workbook_contexts
            task.excel_plan = result.excel_plan
            task.task_plan = result.task_plan
            task.pending_step_id = result.pending_step_id
            task.step_artifacts = result.step_artifacts
            task.current_step_index = result.current_step_index
            task.confirmed_step_ids = result.confirmed_step_ids
            task.raw_llm_response = result.raw_llm_response
            task.execution_steps = result.execution_steps
            task.logs = result.logs
            task.error = result.error
            task.error_message = result.error_message
            task.technical_error = result.technical_error
        except Exception:
            task.status = "failed"
            task.error = "任务执行失败"
            task.error_message = "任务执行失败，请检查执行日志。"
            task.technical_error = traceback.format_exc()
            task.logs.append(traceback.format_exc())

        task.updated_at = self._now()
        return self.save_task(task)

    def start_task_execution(self, task_id: str) -> TaskDetail:
        task = self.get_task(task_id)
        if task.status == "running":
            raise ValueError("Task is already running.")
        if task.status == "completed":
            raise ValueError("Task has already completed.")
        if task.status == "failed":
            raise ValueError("Task has failed. Retry is not supported yet.")
        if task.status not in {"waiting_confirm", "waiting_step_confirm"}:
            raise ValueError("Task status must be waiting_confirm or waiting_step_confirm before execution.")
        if not task.excel_plan and not task.task_plan:
            raise ValueError("Task has no plan to execute.")

        confirmed_step_ids = list(task.confirmed_step_ids)
        if task.status == "waiting_step_confirm" and task.pending_step_id:
            if task.pending_step_id not in confirmed_step_ids:
                confirmed_step_ids.append(task.pending_step_id)

        task.status = "running"
        task.error = None
        task.error_message = None
        task.technical_error = None
        task.confirmed_step_ids = confirmed_step_ids
        task.updated_at = self._now()
        return self.save_task(task)

    def run_task_execution(self, task_id: str) -> None:
        task = self.get_task(task_id)
        confirmed_step_ids = list(task.confirmed_step_ids)
        try:
            state = AgentState(
                task_id=task.task_id,
                message=task.message,
                uploaded_file_path=task.uploaded_file_path,
                uploaded_file_paths=task.uploaded_file_paths,
                uploaded_files=[item.model_dump(mode="json") for item in task.uploaded_files],
                workbook_context=task.workbook_context,
                workbook_contexts=task.workbook_contexts,
                excel_plan=task.excel_plan,
                task_plan=task.task_plan,
                task_mode=task.task_mode,
                step_artifacts=task.step_artifacts,
                current_step_index=task.current_step_index,
                pending_step_id=task.pending_step_id,
                confirmed_step_ids=confirmed_step_ids,
                execution_steps=task.execution_steps,
                logs=task.logs.copy(),
                status=task.status,
            )
            result = AgentState.model_validate(execute_graph.invoke(state))
            task.status = result.status
            task.output_file_path = result.output_file_path
            task.task_plan = result.task_plan
            task.pending_step_id = result.pending_step_id
            task.step_artifacts = result.step_artifacts
            task.current_step_index = result.current_step_index
            task.confirmed_step_ids = result.confirmed_step_ids
            task.execution_steps = result.execution_steps
            task.logs = result.logs
            if result.status == "failed":
                task.error = result.error or "Excel 生成失败"
                task.error_message = result.error_message
                task.technical_error = result.technical_error
            else:
                task.error = None
                task.error_message = None
                task.technical_error = None
        except Exception as exc:
            try:
                persisted = self.get_task(task_id)
                task.execution_steps = persisted.execution_steps
                task.logs = persisted.logs
                task.task_plan = persisted.task_plan
                task.step_artifacts = persisted.step_artifacts
                task.current_step_index = persisted.current_step_index
                task.confirmed_step_ids = persisted.confirmed_step_ids
                task.pending_step_id = persisted.pending_step_id
            except Exception:
                pass
            task.status = "failed"
            task.error = "Excel 生成失败"
            task.error_message = f"Excel 生成失败：{exc}"
            task.technical_error = traceback.format_exc()
            task.logs.append(traceback.format_exc())

        task.updated_at = self._now()
        self.save_task(task)


task_service = TaskService()
