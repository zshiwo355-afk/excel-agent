from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.execution_step import ExecutionStep


TaskStatus = Literal[
    "planning",
    "waiting_confirm",
    "waiting_step_confirm",
    "running",
    "completed",
    "failed",
]


class UploadedFileItem(BaseModel):
    file_id: str
    file_name: str
    file_path: str
    size: int = 0


class TaskDetail(BaseModel):
    task_id: str
    message: str
    status: TaskStatus
    auto_execute: bool = True
    uploaded_file_path: str | None = None
    uploaded_file_paths: list[str] = Field(default_factory=list)
    uploaded_files: list[UploadedFileItem] = Field(default_factory=list)
    output_file_path: str | None = None
    workbook_context: dict[str, Any] | None = None
    workbook_contexts: list[dict[str, Any]] = Field(default_factory=list)
    excel_plan: dict[str, Any] | None = None
    task_plan: dict[str, Any] | None = None
    task_mode: Literal["simple", "complex"] = "simple"
    step_artifacts: dict[str, str] = Field(default_factory=dict)
    current_step_index: int = 0
    confirmed_step_ids: list[str] = Field(default_factory=list)
    pending_step_id: str | None = None
    error: str | None = None
    error_message: str | None = None
    technical_error: str | None = None
    raw_llm_response: dict[str, Any] | str | None = None
    execution_steps: list[ExecutionStep] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
