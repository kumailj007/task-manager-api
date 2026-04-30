"""
Database session management.

Uses SQLite for zero-setup local development. The DATABASE_URL is the
only thing that needs to change to deploy on PostgreSQL or Azure SQL —
no application code changes required. This is a key benefit of using
SQLAlchemy as an abstraction layer.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base

# Local SQLite database file — created automatically on first run.
# In production this would be e.g.
#   "postgresql://user:pass@host/db"
#   "mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+17"
DATABASE_URL = "sqlite:///./tasks.db"

engine = create_engine(
    DATABASE_URL,
    # check_same_thread is SQLite-specific; not needed on PostgreSQL/MSSQL.
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create database tables on startup if they do not exist yet."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    FastAPI dependency that yields a database session per request.

    The session is automatically closed when the request finishes,
    even if an exception is raised. This is the recommended pattern
    in the FastAPI documentation.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()