from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status

from app.schemas.task import TaskDetail
from app.services.task_service import task_service

router = APIRouter(tags=["tasks"])


@router.get("/tasks", response_model=list[TaskDetail])
def list_tasks() -> list[TaskDetail]:
    return task_service.list_tasks()


@router.post("/tasks", response_model=TaskDetail, status_code=status.HTTP_201_CREATED)
async def create_task(
    background_tasks: BackgroundTasks,
    message: str = Form(...),
    file: UploadFile | None = File(default=None),
    files: list[UploadFile] | None = File(default=None),
    auto_execute: bool | None = Form(default=None),
) -> TaskDetail:
    try:
        task = await task_service.create_task(
            message=message,
            upload=file,
            uploads=files,
            auto_execute=auto_execute,
        )
        if task.auto_execute and task.status == "waiting_confirm":
            task = task_service.start_task_execution(task.task_id)
            background_tasks.add_task(task_service.run_task_execution, task.task_id)
        return task
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(task_id: str) -> TaskDetail:
    try:
        return task_service.get_task(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/confirm", response_model=TaskDetail)
def confirm_task(task_id: str, background_tasks: BackgroundTasks) -> TaskDetail:
    try:
        task = task_service.start_task_execution(task_id)
        background_tasks.add_task(task_service.run_task_execution, task_id)
        return task
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
