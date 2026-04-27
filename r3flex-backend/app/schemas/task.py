"""
Task API schemas.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: str = Field(default="open", max_length=50)
    priority: str = Field(default="medium", max_length=50)
    task_type: str = Field(default="operational", max_length=100)
    assignee: Optional[str] = Field(default=None, max_length=255)
    due_at: Optional[datetime] = None
    metadata_json: dict = Field(default_factory=dict)
    disruption_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None
    company_id: Optional[str] = Field(default=None, max_length=255)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = Field(default=None, max_length=50)
    priority: Optional[str] = Field(default=None, max_length=50)
    task_type: Optional[str] = Field(default=None, max_length=100)
    assignee: Optional[str] = Field(default=None, max_length=255)
    due_at: Optional[datetime] = None
    metadata_json: Optional[dict] = None
    disruption_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None


class TaskRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    company_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    task_type: str
    assignee: Optional[str] = None
    due_at: Optional[datetime] = None
    metadata_json: dict = Field(default_factory=dict)
    disruption_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class TaskList(BaseModel):
    items: list[TaskRead]
    total: int

