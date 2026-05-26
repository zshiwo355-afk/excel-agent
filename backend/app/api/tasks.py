from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.task import TaskDetail
from app.services.task_service import task_service

router = APIRouter(tags=["tasks"])


@router.get("/tasks", response_model=list[TaskDetail])
def list_tasks() -> list[TaskDetail]:
    return task_service.list_tasks()


@router.post("/tasks", response_model=TaskDetail, status_code=status.HTTP_201_CREATED)
async def create_task(
    message: str = Form(...),
    file: UploadFile | None = File(default=None),
) -> TaskDetail:
    try:
        return await task_service.create_task(message=message, upload=file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(task_id: str) -> TaskDetail:
    try:
        return task_service.get_task(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/confirm", response_model=TaskDetail)
def confirm_task(task_id: str) -> TaskDetail:
    try:
        return task_service.confirm_task(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
