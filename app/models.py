"""
Domain models for the Task Manager API.

Combines:
  - SQLAlchemy ORM model (TaskORM) for database persistence
  - Pydantic schemas (TaskCreate, TaskUpdate, TaskResponse) for
    request and response validation in the API layer

Keeping them in one module makes the domain easy to navigate.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Priority(str, Enum):
    """Allowed values for a task's priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------- Database model ----------
class TaskORM(Base):
    """How a task looks when stored in the database."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(120), nullable=False)
    description = Column(String(500), nullable=True)
    priority = Column(String(10), nullable=False, default="medium")
    completed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ---------- API schemas ----------
class TaskCreate(BaseModel):
    """Payload for creating a new task."""
    title: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    priority: Priority = Priority.MEDIUM


class TaskUpdate(BaseModel):
    """Payload for updating a task — all fields optional."""
    title: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    priority: Optional[Priority] = None
    completed: Optional[bool] = None


class TaskResponse(BaseModel):
    """How a task is returned by the API."""
    id: int
    title: str
    description: Optional[str]
    priority: Priority
    completed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)