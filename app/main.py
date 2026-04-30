"""
Task Manager API — application entry point.

Wires together:
    - The FastAPI app instance and its OpenAPI metadata
    - Startup logic (initializing the database)
    - The HTTP routes from app.routes
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Code before `yield` runs on startup; code after runs on shutdown.
    We use it here to make sure the database tables exist before the
    first request is served.
    """
    init_db()
    yield


app = FastAPI(
    title="Task Manager API",
    description=(
        "A production-style REST API for task management, built with "
        "Python, FastAPI, and SQLAlchemy. Demonstrates clean architecture, "
        "input validation, persistence, dependency injection, and "
        "automated integration tests."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/", tags=["System"])
def root():
    """Root endpoint — points users to the interactive documentation."""
    return {
        "service": "Task Manager API",
        "documentation": "/docs",
        "endpoints": [
            "/health",
            "/tasks",
            "/tasks/{id}",
            "/stats",
        ],
    }