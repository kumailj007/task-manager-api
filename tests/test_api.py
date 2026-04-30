"""
Integration tests for the Task Manager API.

Uses FastAPI's TestClient to send real HTTP requests to the app
in-memory (no separate server running). Each test is independent and
uses a temporary in-memory SQLite database, so tests never interfere
with the development tasks.db file.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Base


# ----------------------------------------------------------------------
# Test setup — use a separate temporary database for tests
# ----------------------------------------------------------------------
@pytest.fixture(scope="function")
def client():
    """Provide a fresh TestClient backed by a clean temporary database."""
    # Create a fresh temporary SQLite file per test
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    test_url = f"sqlite:///{path}"

    test_engine = create_engine(
        test_url, connect_args={"check_same_thread": False}
    )
    TestSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)

    # Cleanup
    app.dependency_overrides.clear()
    test_engine.dispose()
    os.remove(path)


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_health_check(client):
    """Health endpoint should return a healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "task-manager-api",
    }


def test_create_task(client):
    """Creating a task should return 201 and the created task."""
    payload = {
        "title": "Apply to Azure cloud roles",
        "description": "Target 10 applications",
        "priority": "high",
    }
    response = client.post("/tasks", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == payload["title"]
    assert data["priority"] == "high"
    assert data["completed"] is False
    assert "created_at" in data


def test_get_nonexistent_task_returns_404(client):
    """Requesting a task that does not exist should return 404."""
    response = client.get("/tasks/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_list_tasks(client):
    """Listing tasks should return all created tasks."""
    client.post("/tasks", json={"title": "First task", "priority": "low"})
    client.post("/tasks", json={"title": "Second task", "priority": "high"})

    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_update_task_completion(client):
    """PATCH should be able to mark a task as completed."""
    create = client.post("/tasks", json={"title": "Task to complete"})
    task_id = create.json()["id"]

    response = client.patch(f"/tasks/{task_id}", json={"completed": True})
    assert response.status_code == 200
    assert response.json()["completed"] is True


def test_delete_task(client):
    """DELETE should remove the task and subsequent GET should 404."""
    create = client.post("/tasks", json={"title": "Task to delete"})
    task_id = create.json()["id"]

    delete_response = client.delete(f"/tasks/{task_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404


def test_invalid_priority_is_rejected(client):
    """Pydantic should reject invalid priority values with 422."""
    response = client.post(
        "/tasks", json={"title": "Bad task", "priority": "urgent"}
    )
    assert response.status_code == 422