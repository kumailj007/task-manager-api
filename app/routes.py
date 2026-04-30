"""
HTTP routes for the Task Manager API.

Implements full CRUD (Create, Read, Update, Delete) plus filtering
and aggregate statistics. Each route is a thin layer that:
    1. Validates input via Pydantic (handled automatically)
    2. Talks to the database via SQLAlchemy
    3. Returns a typed response
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Priority,
    TaskCreate,
    TaskORM,
    TaskResponse,
    TaskUpdate,
)

router = APIRouter()


# ----------------------------------------------------------------------
# Health check
# ----------------------------------------------------------------------
@router.get("/health", tags=["System"])
def health_check():
    """Liveness probe — used by load balancers and monitoring systems."""
    return {"status": "healthy", "service": "task-manager-api"}


# ----------------------------------------------------------------------
# Create
# ----------------------------------------------------------------------
@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Tasks"],
)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task and persist it to the database."""
    task = TaskORM(
        title=payload.title,
        description=payload.description,
        priority=payload.priority.value,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ----------------------------------------------------------------------
# Read (list)
# ----------------------------------------------------------------------
@router.get("/tasks", response_model=List[TaskResponse], tags=["Tasks"])
def list_tasks(
    completed: Optional[bool] = Query(
        None, description="Filter by completion status"
    ),
    priority: Optional[Priority] = Query(
        None, description="Filter by priority level"
    ),
    db: Session = Depends(get_db),
):
    """List all tasks, optionally filtered by completion or priority."""
    query = db.query(TaskORM)

    if completed is not None:
        query = query.filter(TaskORM.completed == completed)
    if priority is not None:
        query = query.filter(TaskORM.priority == priority.value)

    return query.order_by(TaskORM.created_at.desc()).all()


# ----------------------------------------------------------------------
# Read (single)
# ----------------------------------------------------------------------
@router.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Retrieve a single task by its ID."""
    task = db.query(TaskORM).filter(TaskORM.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ----------------------------------------------------------------------
# Update
# ----------------------------------------------------------------------
@router.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
):
    """
    Partially update a task — only the fields included in the request
    body will be changed. Useful for e.g. marking a task complete
    without resending the title and description.
    """
    task = db.query(TaskORM).filter(TaskORM.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "priority" and value is not None:
            value = value.value  # convert enum to string for storage
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


# ----------------------------------------------------------------------
# Delete
# ----------------------------------------------------------------------
@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tasks"],
)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task by its ID."""
    task = db.query(TaskORM).filter(TaskORM.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return None


# ----------------------------------------------------------------------
# Aggregate statistics
# ----------------------------------------------------------------------
@router.get("/stats", tags=["Analytics"])
def task_stats(db: Session = Depends(get_db)):
    """Aggregate statistics across all tasks (counts by status & priority)."""
    total = db.query(TaskORM).count()
    completed = db.query(TaskORM).filter(TaskORM.completed.is_(True)).count()
    pending = total - completed

    by_priority = {p.value: 0 for p in Priority}
    for task in db.query(TaskORM).all():
        by_priority[task.priority] += 1

    return {
        "total_tasks": total,
        "completed": completed,
        "pending": pending,
        "by_priority": by_priority,
    }