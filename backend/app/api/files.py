from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.task_service import task_service

router = APIRouter(tags=["files"])


@router.get("/tasks/{task_id}/download")
def download_task_file(task_id: str) -> FileResponse:
    try:
        task = task_service.get_task(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not task.output_file_path:
        raise HTTPException(status_code=404, detail="Task output file not found.")

    output_path = task_service.resolve_existing_file(task.output_file_path)
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=output_path.name,
    )
