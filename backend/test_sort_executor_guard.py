from pathlib import Path

from openpyxl import Workbook

from app.schemas.task import TaskDetail
from app.services.task_service import TaskService


BASE_DIR = Path(__file__).resolve().parent
TMP_DIR = BASE_DIR / "storage" / "tmp_sort_guard_test"


def write_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(["商品", "价格"])
    sheet.append(["A", 10])
    sheet.append(["B", 20])
    workbook.save(path)


def run_sort_executor_guard_test() -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    file_path = TMP_DIR / "input.xlsx"
    write_workbook(file_path)

    context = {
        "file_id": "file_1",
        "file_path": str(file_path),
        "file_name": "input.xlsx",
        "sheet_names": ["Sheet1"],
        "sheets": [
            {
                "name": "Sheet1",
                "header_row": 1,
                "data_start_row": 2,
                "headers": ["商品", "价格"],
            }
        ],
    }

    service = TaskService()
    task_id = "sort-guard-test"
    task = TaskDetail(
        task_id=task_id,
        message="帮我把价格从高到低进行排序",
        status="running",
        auto_execute=True,
        uploaded_file_path=str(file_path),
        uploaded_file_paths=[str(file_path)],
        uploaded_files=[
            {
                "file_id": "file_1",
                "file_name": "input.xlsx",
                "file_path": str(file_path),
                "size": file_path.stat().st_size,
            }
        ],
        workbook_context=context,
        workbook_contexts=[context],
        excel_plan={
            "action": "modify_workbook",
            "workbook_name": "排序结果.xlsx",
            "sheets": [
                {
                    "operation": "sort_rows",
                    "name": "Sheet1",
                    "source_sheet": "Sheet1",
                    "header_row": 1,
                    "data_start_row": 2,
                }
            ],
        },
        logs=["Task created."],
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    service.save_task(task)

    service.run_task_execution(task_id)
    executed = service.get_task(task_id)
    assert executed.status == "failed"
    assert "排序任务缺少排序列或排序方向" in (executed.error_message or "")
    assert executed.execution_steps
    assert executed.execution_steps[0].title == "识别排序列"
    assert executed.execution_steps[0].status == "failed"


if __name__ == "__main__":
    run_sort_executor_guard_test()
    print("sort executor guard test passed")
