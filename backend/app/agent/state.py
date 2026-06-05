from typing import Any

from pydantic import BaseModel, Field

from app.schemas.execution_step import ExecutionStep


class AgentState(BaseModel):
    task_id: str
    message: str
    uploaded_file_path: str | None = None
    uploaded_file_paths: list[str] = Field(default_factory=list)
    uploaded_files: list[dict[str, Any]] = Field(default_factory=list)
    workbook_context: dict[str, Any] | None = None
    workbook_contexts: list[dict[str, Any]] = Field(default_factory=list)
    excel_plan: dict[str, Any] | None = None
    task_plan: dict[str, Any] | None = None
    task_mode: str = "simple"
    step_artifacts: dict[str, str] = Field(default_factory=dict)
    current_step_index: int = 0
    pending_step_id: str | None = None
    confirmed_step_ids: list[str] = Field(default_factory=list)
    status_message: str | None = None
    clarification_question: str | None = None
    clarification_history: list[dict[str, Any]] = Field(default_factory=list)
    last_executed_step_id: str | None = None
    last_step_artifact: str | None = None
    last_step_result: dict[str, Any] | None = None
    raw_llm_response: dict[str, Any] | str | None = None
    output_file_path: str | None = None
    execution_steps: list[ExecutionStep] = Field(default_factory=list)
    status: str = "planning"
    logs: list[str] = Field(default_factory=list)
    error: str | None = None
    error_message: str | None = None
    technical_error: str | None = None
