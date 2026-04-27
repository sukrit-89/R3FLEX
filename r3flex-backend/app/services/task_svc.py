"""
Task service.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate

settings = get_settings()


class TaskService:
    @staticmethod
    async def create(payload: TaskCreate, db: AsyncSession) -> Task:
        task = Task(
            company_id=payload.company_id or settings.company_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            task_type=payload.task_type,
            assignee=payload.assignee,
            due_at=payload.due_at,
            metadata_json=payload.metadata_json,
            disruption_id=payload.disruption_id,
            supplier_id=payload.supplier_id,
        )
        db.add(task)
        await db.flush()
        return task

    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        company_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Task], int]:
        scope_company = company_id or settings.company_id
        query = select(Task).where(Task.company_id == scope_company)
        count_query = select(func.count(Task.id)).where(Task.company_id == scope_company)
        if status:
            query = query.where(Task.status == status)
            count_query = count_query.where(Task.status == status)
        result = await db.execute(query.order_by(Task.created_at.desc()))
        count_result = await db.execute(count_query)
        return list(result.scalars().all()), count_result.scalar() or 0

    @staticmethod
    async def get(task_id: uuid.UUID, db: AsyncSession) -> Task | None:
        result = await db.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update(task_id: uuid.UUID, payload: TaskUpdate, db: AsyncSession) -> Task | None:
        task = await TaskService.get(task_id, db)
        if not task:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
        await db.flush()
        return task

    @staticmethod
    async def create_many(payloads: list[TaskCreate], db: AsyncSession) -> list[Task]:
        created: list[Task] = []
        for payload in payloads:
            created.append(await TaskService.create(payload, db))
        return created
