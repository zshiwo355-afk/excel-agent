from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class MetricPlan(BaseModel):
    name: str
    source_column: str
    aggregation: Literal["sum", "count", "avg", "max", "min"]


class StylePlan(BaseModel):
    freeze_header: bool = False
    auto_filter: bool = False
    auto_width: bool = False
    header_bold: bool = False


class SortPlan(BaseModel):
    column: str
    order: Literal["asc", "desc"]
    numeric: bool = True


class CleanPlan(BaseModel):
    remove_empty_rows: bool = False
    trim_text: bool = False


class FormulaPlan(BaseModel):
    target_cell: str
    expression: str


class SheetPlan(BaseModel):
    operation: Literal[
        "create_sheet",
        "append_columns",
        "create_summary_sheet",
        "format_sheet",
        "sort_rows",
        "clean_sheet",
        "format_and_sort_sheet",
    ]
    name: str
    columns: list[str] | None = None
    sample_rows: int | None = None
    source_sheet: str | None = None
    header_row: int | None = None
    data_start_row: int | None = None
    data_end_row: int | None = None
    group_by: list[str] | None = None
    metrics: list[MetricPlan] | None = None
    style: StylePlan | None = None
    sort: SortPlan | None = None
    clean: CleanPlan | None = None
    rows: list[dict[str, Any]] | None = None
    formulas: list[FormulaPlan] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Sheet name cannot be empty.")
        if len(value) > 31:
            raise ValueError("Sheet name cannot exceed 31 characters.")
        return value


class ExcelPlan(BaseModel):
    action: Literal["create_workbook", "modify_workbook"]
    workbook_name: str = Field(min_length=1)
    sheets: list[SheetPlan]
    notes: list[str] = Field(default_factory=list)

    @field_validator("workbook_name")
    @classmethod
    def validate_workbook_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("workbook_name cannot be empty.")
        if not value.endswith(".xlsx"):
            value = f"{value}.xlsx"
        return value


def summarize_excel_plan_validation_error(missing_fields: list[str] | None = None) -> str:
    if missing_fields:
        return (
            "DeepSeek 返回的 ExcelPlan 缺少 "
            + "/".join(missing_fields)
            + "，请检查 planner 输出。"
        )
    return "DeepSeek 返回的 ExcelPlan 结构不符合要求，请检查 planner 输出。"
