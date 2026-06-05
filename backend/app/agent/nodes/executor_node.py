from pathlib import Path
from time import sleep
from uuid import uuid4

from app.agent.state import AgentState
from app.config import get_settings
from app.excel_tools.builder import create_workbook_from_plan
from app.excel_tools.merger import merge_workbooks_by_plan
from app.excel_tools.modifier import (
    apply_named_style_step,
    copy_workbook_for_simple_execution,
    execute_simple_sheet_operation,
    modify_workbook_from_plan,
    resolve_target_date_columns,
    save_simple_execution_workbook,
)
from app.excel_tools.splitter import split_workbook_by_column
from app.excel_tools.template_applier import apply_template_sheet_from_plan
from app.excel_tools.validator import validate_output_workbook
from app.schemas.execution_step import ExecutionStep
from app.schemas.excel_plan import ExcelPlan


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _append_step(
    state: AgentState,
    *,
    title: str,
    detail: str,
    tool_name: str | None = None,
) -> ExecutionStep:
    step = ExecutionStep(
        step_id=uuid4().hex,
        title=title,
        status="pending",
        detail=detail,
        tool_name=tool_name,
    )
    state.execution_steps.append(step)
    return step


def _save_runtime_state(state: AgentState) -> None:
    from app.services.task_service import task_service

    task_service.save_runtime_state(state)


def _step_debug_delay_seconds() -> float:
    settings = get_settings()
    return max(settings.excel_agent_step_debug_delay_ms, 0) / 1000


def _apply_step_debug_delay() -> None:
    delay_seconds = _step_debug_delay_seconds()
    if delay_seconds > 0:
        sleep(delay_seconds)


def _update_step(
    state: AgentState,
    step: ExecutionStep,
    *,
    status: str,
    result_summary: str | None = None,
    detail: str | None = None,
) -> None:
    if status == "running" and not step.started_at:
        step.started_at = _now()
    if status in {"completed", "failed"}:
        step.ended_at = _now()
    step.status = status
    if result_summary is not None:
        step.result_summary = result_summary
    if detail is not None:
        step.detail = detail
    _save_runtime_state(state)


def _run_simple_step(
    state: AgentState,
    *,
    title: str,
    detail: str,
    action,
    tool_name: str | None = None,
    result_summary: str | None = None,
):
    step = _append_step(state, title=title, detail=detail, tool_name=tool_name)
    state.logs.append(f"{title} started: {detail}")
    _update_step(state, step, status="running")
    try:
        action()
        _apply_step_debug_delay()
        summary = result_summary or "执行完成"
        state.logs.append(f"{title} completed: {summary}")
        _update_step(state, step, status="completed", result_summary=summary)
    except Exception as exc:
        state.logs.append(f"{title} failed: {exc}")
        _update_step(state, step, status="failed", result_summary=str(exc))
        raise


def _style_actions_for_sheet(sheet_plan):
    if not sheet_plan.style:
        return []
    actions = []
    if sheet_plan.style.freeze_header:
        actions.append(("冻结表头", "freeze_header"))
    if sheet_plan.style.auto_filter:
        actions.append(("开启筛选", "auto_filter"))
    if sheet_plan.style.auto_width:
        actions.append(("自动调整列宽", "auto_width"))
    if sheet_plan.style.header_bold:
        actions.append(("表头加粗", "header_bold"))
    return actions


def _run_validation(output_path, plan, workbook_contexts, validation_holder: dict) -> None:
    validation = validate_output_workbook(output_path, plan, workbook_contexts)
    validation_holder.update(validation)
    if not validation.get("ok"):
        raise ValueError(validation.get("message", "结果文件校验失败"))


def _require_sort_config(sheet_plan) -> None:
    if not sheet_plan.sort or not sheet_plan.sort.column or not sheet_plan.sort.order:
        raise ValueError("排序任务缺少排序列或排序方向，请指定按哪一列排序。")


def _execute_simple_plan_with_steps(state: AgentState, plan: ExcelPlan, output_path: Path) -> None:
    if plan.action == "create_workbook":
        _run_simple_step(
            state,
            title="生成结果文件",
            detail=f"创建工作簿 {output_path.name}",
            action=lambda: create_workbook_from_plan(plan, output_path),
            tool_name="create_workbook_from_plan",
            result_summary=f"已生成 {output_path.name}",
        )
        return

    if not state.uploaded_file_path:
        raise ValueError("Uploaded workbook is required for modify_workbook.")

    workbook = copy_workbook_for_simple_execution(Path(state.uploaded_file_path), output_path)
    _save_runtime_state(state)

    for sheet_plan in plan.sheets:
        target_name = sheet_plan.source_sheet or sheet_plan.name
        base_detail = f"Sheet: {target_name}"

        if sheet_plan.operation in {"append_columns", "create_summary_sheet", "clean_sheet", "create_sheet"}:
            _run_simple_step(
                state,
                title=f"执行操作：{sheet_plan.operation}",
                detail=base_detail,
                action=lambda sp=sheet_plan: execute_simple_sheet_operation(workbook, sp),
                tool_name=sheet_plan.operation,
                result_summary=f"{sheet_plan.operation} 已完成",
            )

        if sheet_plan.operation == "update_date_month":
            target_month = sheet_plan.date_update.target_month if sheet_plan.date_update else "?"
            sheet = workbook[target_name]
            detected_columns = {}
            _run_simple_step(
                state,
                title="识别日期列",
                detail=base_detail,
                action=lambda sp=sheet_plan, sh=sheet: detected_columns.update({"columns": resolve_target_date_columns(sh, sp)}),
                tool_name="resolve_target_date_columns",
                result_summary="已识别日期列",
            )
            _run_simple_step(
                state,
                title=f"修改日期为 {target_month} 月",
                detail=base_detail,
                action=lambda sp=sheet_plan: execute_simple_sheet_operation(workbook, sp),
                tool_name="update_date_month",
                result_summary=f"已将日期月份修改为 {target_month} 月",
            )

        if sheet_plan.operation == "fill_column_with_value":
            column_name = sheet_plan.fill.column_name if sheet_plan.fill else "目标列"
            label = "填充今天日期" if sheet_plan.fill and sheet_plan.fill.value_mode == "today_date" else f"填充列 {column_name}"
            _run_simple_step(
                state,
                title=label,
                detail=base_detail,
                action=lambda sp=sheet_plan: execute_simple_sheet_operation(workbook, sp),
                tool_name="fill_column_with_value",
                result_summary=f"已写入列：{column_name}",
            )

        if sheet_plan.operation == "format_and_sort_sheet":
            _run_simple_step(
                state,
                title="识别排序列",
                detail=base_detail,
                action=lambda sp=sheet_plan: _require_sort_config(sp),
                tool_name="sort_plan_check",
                result_summary=f"已识别排序列：{sheet_plan.sort.column}" if sheet_plan.sort and sheet_plan.sort.column else None,
            )
            _run_simple_step(
                state,
                title=f"按 {sheet_plan.sort.column} {'从高到低' if sheet_plan.sort.order == 'desc' else '从低到高'}排序",
                detail=base_detail,
                action=lambda sp=sheet_plan: execute_simple_sheet_operation(workbook, sp),
                tool_name="format_and_sort_sheet",
                result_summary="清洗与排序完成",
            )

        if sheet_plan.operation == "sort_rows":
            _run_simple_step(
                state,
                title="识别排序列",
                detail=base_detail,
                action=lambda sp=sheet_plan: _require_sort_config(sp),
                tool_name="sort_plan_check",
                result_summary=f"已识别排序列：{sheet_plan.sort.column}" if sheet_plan.sort and sheet_plan.sort.column else None,
            )
            _run_simple_step(
                state,
                title=f"按 {sheet_plan.sort.column} {'从高到低' if sheet_plan.sort.order == 'desc' else '从低到高'}排序",
                detail=base_detail,
                action=lambda sp=sheet_plan: execute_simple_sheet_operation(workbook, sp),
                tool_name="sort_rows",
                result_summary="排序完成",
            )

        if sheet_plan.operation in {"format_sheet", "format_and_sort_sheet"}:
            sheet = workbook[target_name]
            for title, action_name in _style_actions_for_sheet(sheet_plan):
                _run_simple_step(
                    state,
                    title=title,
                    detail=base_detail,
                    action=lambda sh=sheet, name=action_name: apply_named_style_step(sh, name),
                    tool_name="formatter",
                    result_summary=f"{title} 已完成",
                )

    _run_simple_step(
        state,
        title="生成结果文件",
        detail=f"写入 {output_path.name}",
        action=lambda: save_simple_execution_workbook(workbook, output_path),
        tool_name="workbook.save",
        result_summary=f"已写入 {output_path.name}",
    )


def executor_node(state: AgentState) -> AgentState:
    state = AgentState.model_validate(state)
    settings = get_settings()
    plan = ExcelPlan.model_validate(state.excel_plan)
    output_dir = settings.outputs_dir / state.task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{Path(plan.workbook_name).stem}.xlsx"

    if plan.action == "merge_workbooks":
        state.logs.append("Executing merge_workbooks.")
        for source_sheet in plan.merge.source_sheets if plan.merge else []:
            state.logs.append(f"Merging sheet {source_sheet.file_name} / {source_sheet.sheet_name}")
        merge_workbooks_by_plan(plan, state.workbook_contexts, output_path)
    else:
        state.logs.append("Executing ExcelPlan.")
        split_sheet_plan = next((sheet for sheet in plan.sheets if sheet.operation == "split_sheet_by_column"), None)
        template_sheet_plan = next((sheet for sheet in plan.sheets if sheet.operation == "apply_template_sheet"), None)
        if template_sheet_plan:
            template = template_sheet_plan.template
            state.logs.append(
                f"Applying template sheet {template.template_sheet} from {template.template_file_id} to source {template.source_sheet or template_sheet_plan.source_sheet}"
            )
            apply_template_sheet_from_plan(plan, state.uploaded_files, output_path)
            if template_sheet_plan.sort:
                state.logs.append(
                    f"Sorting templated output by column {template_sheet_plan.sort.column} {template_sheet_plan.sort.order}"
                )
        elif split_sheet_plan:
            state.logs.append(
                f"Splitting sheet {split_sheet_plan.source_sheet} by column {split_sheet_plan.split.column}"
            )
            if not state.uploaded_file_path:
                raise ValueError("Uploaded workbook is required for split_sheet_by_column.")
            split_result = split_workbook_by_column(plan, Path(state.uploaded_file_path), output_path)
            for sheet_name in split_result["created_sheet_names"]:
                state.logs.append(f"Created sheet for value: {sheet_name}")
            state.logs.append(f"Created split sheets: {split_result['total_split_sheets']}")
        else:
            if state.workbook_context and any(
                sheet.get("merged_cells") for sheet in state.workbook_context.get("sheets", [])
            ):
                state.logs.append("Detected merged cells, safe formatting mode enabled.")
            for sheet_plan in plan.sheets:
                target_name = sheet_plan.source_sheet or sheet_plan.name
                if sheet_plan.header_row:
                    state.logs.append(f"Detected header row: {sheet_plan.header_row}")
                if sheet_plan.data_start_row:
                    state.logs.append(f"Detected data start row: {sheet_plan.data_start_row}")
                if sheet_plan.style:
                    state.logs.append(f"Applying style to sheet: {target_name}")
                if sheet_plan.sort:
                    state.logs.append(
                        f"Sorting sheet {target_name} by column {sheet_plan.sort.column} {sheet_plan.sort.order}"
                    )
                if sheet_plan.operation == "fill_column_with_value" and sheet_plan.fill:
                    state.logs.append(
                        f"Filling column {sheet_plan.fill.column_name} on sheet {target_name} with {sheet_plan.fill.value_mode}"
                    )
            _execute_simple_plan_with_steps(state, plan, output_path)

    validation_holder = {}
    _run_simple_step(
        state,
        title="校验结果文件",
        detail=f"校验 {output_path.name}",
        action=lambda: _run_validation(output_path, plan, state.workbook_contexts, validation_holder),
        tool_name="validate_output_workbook",
        result_summary="文件校验通过",
    )
    validation = validation_holder
    if plan.action == "merge_workbooks":
        state.logs.append(f"Expected merged rows: {validation.get('expected_rows', 0)}")
        state.logs.append(f"Actual merged rows: {validation.get('actual_rows', 0)}")
        state.logs.append("Merge validation completed")
    else:
        state.logs.append("Workbook validation completed")
    if not validation["ok"]:
        raise ValueError(validation["message"])

    state.output_file_path = str(output_path)
    state.logs.append(f"Workbook written to {output_path}.")
    return state
