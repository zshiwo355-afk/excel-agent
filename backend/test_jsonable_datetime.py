import json
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from app.excel_tools.profiler import profile_workbook
from app.utils.jsonable import to_jsonable


BASE_DIR = Path(__file__).resolve().parent
TMP_DIR = BASE_DIR / "storage" / "tmp_jsonable_test"


def write_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(["日期", "事项"])
    sheet.append([datetime(2026, 1, 8, 9, 30, 0), "A"])
    workbook.save(path)


def run_jsonable_datetime_test() -> None:
    payload = {
        "dt": datetime(2026, 1, 8, 9, 30, 0),
        "items": [datetime(2026, 1, 9, 10, 0, 0)],
        "path": TMP_DIR,
        "nan": float("nan"),
    }
    safe_payload = to_jsonable(payload)
    dumped = json.dumps(safe_payload, ensure_ascii=False)
    assert "2026-01-08T09:30:00" in dumped
    assert safe_payload["nan"] is None

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    file_path = TMP_DIR / "input.xlsx"
    write_workbook(file_path)
    context = profile_workbook(file_path, file_id="file_1", file_name="input.xlsx")
    dumped_context = json.dumps(context, ensure_ascii=False)
    assert "2026-01-08T09:30:00" in dumped_context


if __name__ == "__main__":
    run_jsonable_datetime_test()
    print("jsonable datetime test passed")
