import shutil
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings


class FileService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _validate_upload(self, upload: UploadFile) -> None:
        suffix = Path(upload.filename or "upload.xlsx").suffix.lower()
        if suffix != ".xlsx":
            raise ValueError("Only .xlsx files are supported in this version.")

    async def save_upload(self, task_id: str, upload: UploadFile) -> Path:
        self._validate_upload(upload)
        task_dir = self.settings.uploads_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        output_path = task_dir / (upload.filename or "uploaded.xlsx")

        with output_path.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)
        return output_path

    async def save_uploads(self, task_id: str, uploads: list[UploadFile]) -> list[dict[str, object]]:
        saved_files: list[dict[str, object]] = []
        for index, upload in enumerate(uploads, start=1):
            self._validate_upload(upload)
            output_path = await self.save_upload(task_id, upload)
            size = output_path.stat().st_size if output_path.exists() else 0
            saved_files.append(
                {
                    "file_id": f"file_{index}",
                    "file_name": output_path.name,
                    "file_path": str(output_path),
                    "size": size,
                }
            )
        return saved_files

    def ensure_path(self, value: str | Path) -> Path:
        path = Path(value)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path


file_service = FileService()
