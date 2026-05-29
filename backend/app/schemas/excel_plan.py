from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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


class DateUpdatePlan(BaseModel):
    target_month: int
    target_columns: list[str] = Field(default_factory=list)
    match_mode: Literal["date_column", "date_cells"] = "date_column"
    preserve_year: bool = True
    preserve_day: bool = True

    @model_validator(mode="after")
    def validate_date_update(self):
        if not 1 <= self.target_month <= 12:
            raise ValueError("date_update.target_month must be between 1 and 12.")
        return self


class TemplateSheetPlan(BaseModel):
    template_file_id: str
    template_sheet: str
    source_file_id: str | None = None
    source_sheet: str | None = None
    output_sheet_name: str | None = None
    column_mapping: dict[str, str] = Field(default_factory=dict)
    preserve_template_styles: bool = True
    preserve_column_widths: bool = True
    preserve_row_heights: bool = True
    preserve_merged_cells: bool = True
    clear_existing_data_rows: bool = True
    data_start_row: int | None = None

    @model_validator(mode="after")
    def validate_template(self):
        self.template_file_id = self.template_file_id.strip()
        self.template_sheet = self.template_sheet.strip()
        if not self.template_file_id:
            raise ValueError("template.template_file_id cannot be empty.")
        if not self.template_sheet:
            raise ValueError("template.template_sheet cannot be empty.")
        if self.output_sheet_name is not None:
            self.output_sheet_name = self.output_sheet_name.strip() or None
        return self


class SplitPlan(BaseModel):
    column: str
    target_mode: Literal["sheet_per_value"] = "sheet_per_value"
    include_source_sheet: bool = True
    sanitize_sheet_name: bool = True

    @model_validator(mode="after")
    def validate_split(self):
        self.column = self.column.strip()
        if not self.column:
            raise ValueError("split.column cannot be empty.")
        return self


class MergeSourceSheet(BaseModel):
    file_id: str
    file_name: str
    sheet_name: str
    header_row: int
    data_start_row: int

    @model_validator(mode="after")
    def validate_rows(self):
        if self.header_row <= 0 or self.data_start_row <= 0:
            raise ValueError("header_row and data_start_row must be positive integers.")
        return self


class MergePlan(BaseModel):
    mode: Literal["append_rows"] = "append_rows"
    target_sheet_name: str
    source_sheets: list[MergeSourceSheet]
    column_mapping: dict[str, list[str]] = Field(default_factory=dict)
    add_source_columns: bool = True
    source_columns: list[str] = Field(default_factory=lambda: ["来源文件", "来源Sheet"])

    @model_validator(mode="after")
    def validate_merge(self):
        if not self.target_sheet_name.strip():
            raise ValueError("target_sheet_name cannot be empty.")
        if len(self.source_sheets) < 2:
            raise ValueError("merge source_sheets must contain at least two items.")
        if self.mode != "append_rows":
            raise ValueError("Only append_rows is supported.")
        return self


class SheetPlan(BaseModel):
    operation: Literal[
        "create_sheet",
        "append_columns",
        "create_summary_sheet",
        "format_sheet",
        "sort_rows",
        "clean_sheet",
        "format_and_sort_sheet",
        "split_sheet_by_column",
        "apply_template_sheet",
        "update_date_month",
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
    split: SplitPlan | None = None
    template: TemplateSheetPlan | None = None
    date_update: DateUpdatePlan | None = None
    rows: list[dict[str, Any]] | None = None
    formulas: list[FormulaPlan] | None = None

    @model_validator(mode="after")
    def validate_name(self):
        value = self.name.strip()
        if not value:
            raise ValueError("Sheet name cannot be empty.")
        if len(value) > 31:
            raise ValueError("Sheet name cannot exceed 31 characters.")
        self.name = value
        if self.operation == "split_sheet_by_column":
            if not self.split:
                raise ValueError("split_sheet_by_column requires split.")
            if not self.source_sheet:
                raise ValueError("split_sheet_by_column requires source_sheet.")
        if self.operation == "apply_template_sheet":
            if not self.template:
                raise ValueError("apply_template_sheet requires template.")
            if not self.source_sheet and not self.template.source_sheet:
                raise ValueError("apply_template_sheet requires source_sheet.")
        if self.operation == "update_date_month":
            if not self.date_update:
                raise ValueError("update_date_month requires date_update.")
            if not self.source_sheet:
                raise ValueError("update_date_month requires source_sheet.")
        return self


class ExcelPlan(BaseModel):
    action: Literal["create_workbook", "modify_workbook", "merge_workbooks"]
    workbook_name: str = Field(min_length=1)
    sheets: list[SheetPlan] = Field(default_factory=list)
    merge: MergePlan | None = None
    style: StylePlan | None = None
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_plan(self):
        value = self.workbook_name.strip()
        if not value:
            raise ValueError("workbook_name cannot be empty.")
        if not value.endswith(".xlsx"):
            value = f"{value}.xlsx"
        self.workbook_name = value

        if self.action == "merge_workbooks":
            if not self.merge:
                raise ValueError("merge_workbooks requires merge.")
            if self.merge.mode != "append_rows":
                raise ValueError("merge_workbooks only supports append_rows.")
        elif not self.sheets:
            raise ValueError("sheets cannot be empty.")
        return self


def summarize_excel_plan_validation_error(missing_fields: list[str] | None = None) -> str:
    if missing_fields:
        return "ExcelPlan 缺少必填字段：" + "/".join(missing_fields)
    return "ExcelPlan 结构不符合要求，请检查 planner 输出。"
