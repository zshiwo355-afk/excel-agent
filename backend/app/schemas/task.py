from typing import Any, Literal

from pydantic import BaseModel, Field


TaskStatus = Literal["planning", "waiting_confirm", "running", "completed", "failed"]


class TaskDetail(BaseModel):
    task_id: str
    message: str
    status: TaskStatus
    uploaded_file_path: str | None = None
    output_file_path: str | None = None
    workbook_context: dict[str, Any] | None = None
    excel_plan: dict[str, Any] | None = None
    error: str | None = None
    error_message: str | None = None
    technical_error: str | None = None
    raw_llm_response: dict[str, Any] | str | None = None
    logs: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
