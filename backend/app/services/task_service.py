import json
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.agent.graph import execute_graph
from app.agent.nodes.file_analyze_node import file_analyze_node
from app.agent.nodes.intent_node import intent_node
from app.agent.nodes.plan_validate_node import plan_validate_node
from app.agent.nodes.planner_node import planner_node
from app.agent.nodes.task_decomposer_node import task_decomposer_node
from app.agent.state import AgentState
from app.config import get_settings
from app.services.file_service import file_service
from app.schemas.execution_step import ExecutionStep
from app.schemas.task import ClarificationTurn, TaskDetail
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
        task.status_message = state.status_message
        task.clarification_question = state.clarification_question
        task.clarification_history = [
            turn if isinstance(turn, ClarificationTurn) else ClarificationTurn.model_validate(turn)
            for turn in state.clarification_history
        ]
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

    def delete_task(self, task_id: str) -> None:
        task = self.get_task(task_id)

        artifact_paths = []
        if task.output_file_path:
            artifact_paths.append(Path(task.output_file_path))
        artifact_paths.extend(Path(path) for path in task.step_artifacts.values())
        artifact_paths.extend(Path(item.file_path) for item in task.uploaded_files if item.file_path)

        for path in artifact_paths:
            try:
                if path.exists() and path.is_file():
                    path.unlink()
            except Exception:
                pass

        for directory in (self.settings.uploads_dir / task_id, self.settings.outputs_dir / task_id):
            if directory.exists():
                shutil.rmtree(directory, ignore_errors=True)

        task_path = self._task_path(task_id)
        if task_path.exists():
            task_path.unlink()

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
            status_message="正在分析文件",
            auto_execute=self.settings.auto_execute_default if auto_execute is None else auto_execute,
            uploaded_file_path=uploaded_file_path,
            uploaded_file_paths=uploaded_file_paths,
            uploaded_files=uploaded_files,
            created_at=self._now(),
            updated_at=self._now(),
            logs=logs,
        )
        return self.save_task(task)

    def _compose_message_for_planning(self, task: TaskDetail) -> str:
        sections = [task.message.strip()]
        for turn in task.clarification_history:
            sections.append(f"Agent 追问：{turn.question}")
            if turn.answer:
                sections.append(f"用户补充：{turn.answer}")
        return "\n\n".join(section for section in sections if section)

    def _build_agent_state_from_task(self, task: TaskDetail) -> AgentState:
        return AgentState(
            task_id=task.task_id,
            message=self._compose_message_for_planning(task),
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
            confirmed_step_ids=list(task.confirmed_step_ids),
            status_message=task.status_message,
            clarification_question=task.clarification_question,
            clarification_history=[turn.model_dump(mode="json") for turn in task.clarification_history],
            raw_llm_response=task.raw_llm_response,
            execution_steps=task.execution_steps,
            logs=task.logs.copy(),
            status=task.status,
            error=task.error,
            error_message=task.error_message,
            technical_error=task.technical_error,
        )

    def _set_planning_stage(self, state: AgentState, message: str) -> None:
        state.status = "planning"
        state.status_message = message
        state.error = None
        state.error_message = None
        state.technical_error = None
        state.clarification_question = None

    def run_task_planning(self, task_id: str) -> None:
        task = self.get_task(task_id)
        state = self._build_agent_state_from_task(task)

        try:
            planning_stages = (
                ("正在分析文件", file_analyze_node),
                ("正在理解需求", intent_node),
            )
            for message, node in planning_stages:
                self._set_planning_stage(state, message)
                self.save_runtime_state(state)
                state = AgentState.model_validate(node(state))
                self.save_runtime_state(state)
                if state.status in {"failed", "needs_input"}:
                    return

            if state.task_mode == "complex":
                self._set_planning_stage(state, "正在生成执行计划")
                self.save_runtime_state(state)
                state = AgentState.model_validate(task_decomposer_node(state))
                self.save_runtime_state(state)
            else:
                self._set_planning_stage(state, "正在生成执行计划")
                self.save_runtime_state(state)
                state = AgentState.model_validate(planner_node(state))
                self.save_runtime_state(state)
                if state.status not in {"failed", "needs_input"}:
                    self._set_planning_stage(state, "正在校验执行计划")
                    self.save_runtime_state(state)
                    state = AgentState.model_validate(plan_validate_node(state))
                    self.save_runtime_state(state)

            if task.auto_execute and state.status == "waiting_confirm":
                self.start_task_execution(task_id)
                self.run_task_execution(task_id)
        except Exception:
            task = self.get_task(task_id)
            task.status = "failed"
            task.status_message = "思考失败"
            task.error = "任务执行失败"
            task.error_message = "任务执行失败，请检查执行日志。"
            task.technical_error = traceback.format_exc()
            task.logs.append(traceback.format_exc())
            task.updated_at = self._now()
            self.save_task(task)

    def reply_to_task(self, task_id: str, answer: str) -> TaskDetail:
        task = self.get_task(task_id)
        if task.status != "needs_input":
            raise ValueError("Task is not waiting for clarification.")
        trimmed = answer.strip()
        if not trimmed:
            raise ValueError("answer cannot be empty.")

        updated_history: list[ClarificationTurn] = []
        answered = False
        for turn in task.clarification_history:
            if not answered and turn.answer is None:
                updated_history.append(
                    turn.model_copy(update={"answer": trimmed, "answered_at": self._now()})
                )
                answered = True
            else:
                updated_history.append(turn)
        if not answered and task.clarification_question:
            updated_history.append(
                ClarificationTurn(
                    question=task.clarification_question,
                    answer=trimmed,
                    created_at=self._now(),
                    answered_at=self._now(),
                )
            )

        task.status = "planning"
        task.status_message = "正在理解补充信息"
        task.clarification_question = None
        task.clarification_history = updated_history
        task.excel_plan = None
        task.task_plan = None
        task.error = None
        task.error_message = None
        task.technical_error = None
        task.raw_llm_response = None
        task.updated_at = self._now()
        task.logs.append("User clarification received. Planning resumed.")
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
        task.status_message = "开始执行"
        task.clarification_question = None
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
            state = self._build_agent_state_from_task(task)
            state.confirmed_step_ids = confirmed_step_ids
            state.status_message = "正在执行"
            result = AgentState.model_validate(execute_graph.invoke(state))
            task.status = result.status
            task.output_file_path = result.output_file_path
            task.task_plan = result.task_plan
            task.pending_step_id = result.pending_step_id
            task.step_artifacts = result.step_artifacts
            task.current_step_index = result.current_step_index
            task.confirmed_step_ids = result.confirmed_step_ids
            task.status_message = result.status_message
            task.clarification_question = result.clarification_question
            task.clarification_history = [
                turn if isinstance(turn, ClarificationTurn) else ClarificationTurn.model_validate(turn)
                for turn in result.clarification_history
            ]
            task.execution_steps = result.execution_steps
            task.logs = result.logs
            if result.status == "failed":
                task.status_message = "执行失败"
                task.error = result.error or "Excel 生成失败"
                task.error_message = result.error_message
                task.technical_error = result.technical_error
            else:
                if result.status == "completed":
                    task.status_message = "执行完成"
                elif result.status == "waiting_step_confirm":
                    task.status_message = "等待步骤确认"
                else:
                    task.status_message = result.status_message or "正在执行"
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
            task.status_message = "执行失败"
            task.error = "Excel 生成失败"
            task.error_message = f"Excel 生成失败：{exc}"
            task.technical_error = traceback.format_exc()
            task.logs.append(traceback.format_exc())

        task.updated_at = self._now()
        self.save_task(task)


task_service = TaskService()
