import shutil
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings


class FileService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def save_upload(self, task_id: str, upload: UploadFile) -> Path:
        suffix = Path(upload.filename or "upload.xlsx").suffix.lower()
        if suffix != ".xlsx":
            raise ValueError("Only .xlsx files are supported in this version.")

        task_dir = self.settings.uploads_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        output_path = task_dir / (upload.filename or "uploaded.xlsx")

        with output_path.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)
        return output_path

    def ensure_path(self, value: str | Path) -> Path:
        path = Path(value)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path


file_service = FileService()
