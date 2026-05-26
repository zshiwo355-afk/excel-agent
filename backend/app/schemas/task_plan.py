from typing import Any, Literal

from pydantic import BaseModel, Field


StepType = Literal[
    "analyze_files",
    "confirm_column_mapping",
    "merge_workbooks",
    "deduplicate_rows",
    "clean_rows",
    "create_summary_sheet",
    "sort_rows",
    "format_sheet",
    "create_chart",
    "create_exception_sheet",
    "validate_workbook",
    "export_workbook",
]

StepStatus = Literal["pending", "running", "completed", "failed", "waiting_confirm"]


class StepPlan(BaseModel):
    step_id: str
    step_type: StepType
    title: str
    description: str
    input_artifact: str | None = None
    output_artifact: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    requires_user_confirm: bool = False
    status: StepStatus = "pending"
    validation_result: dict[str, Any] | None = None
    error: str | None = None


class TaskPlan(BaseModel):
    task_type: Literal["complex_excel_workflow"] = "complex_excel_workflow"
    goal: str
    steps: list[StepPlan]
    requires_confirmation: bool = False
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
