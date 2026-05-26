from typing import Any

from pydantic import BaseModel, Field


class AgentState(BaseModel):
    task_id: str
    message: str
    uploaded_file_path: str | None = None
    workbook_context: dict[str, Any] | None = None
    excel_plan: dict[str, Any] | None = None
    raw_llm_response: dict[str, Any] | str | None = None
    output_file_path: str | None = None
    status: str = "planning"
    logs: list[str] = Field(default_factory=list)
    error: str | None = None
    error_message: str | None = None
    technical_error: str | None = None
