from typing import Literal

from pydantic import BaseModel


ExecutionStepStatus = Literal["pending", "running", "completed", "failed"]


class ExecutionStep(BaseModel):
    step_id: str
    title: str
    status: ExecutionStepStatus
    detail: str = ""
    started_at: str | None = None
    ended_at: str | None = None
    result_summary: str | None = None
    tool_name: str | None = None
