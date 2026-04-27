"""
Task management router.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.task import TaskCreate, TaskList, TaskRead, TaskUpdate
from app.services.task_svc import TaskService

router = APIRouter()


@router.get("", response_model=TaskList)
async def list_tasks(
    company_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> TaskList:
    items, total = await TaskService.list_tasks(db, company_id=company_id, status=status)
    return TaskList(items=[TaskRead.model_validate(item) for item in items], total=total)


@router.post("", response_model=TaskRead, status_code=201)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    task = await TaskService.create(payload, db)
    return TaskRead.model_validate(task)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    try:
        uid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format.")
    task = await TaskService.update(uid, payload, db)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    return TaskRead.model_validate(task)
