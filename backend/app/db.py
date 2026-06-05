import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def resolve_db_path(data_dir: str | None) -> Path:
    """Where the SQLite database lives.

    Packaged builds pass a writable, persistent per-user directory via
    SANTE_DATA_DIR (Electron sets it to its userData path, e.g.
    %APPDATA%\\Santé on Windows). With no env var, fall back to the
    repo-local backend/database.db used in development.
    """
    if data_dir:
        return Path(data_dir) / "database.db"
    return Path(__file__).resolve().parent.parent / "database.db"


DB_PATH = resolve_db_path(os.environ.get("SANTE_DATA_DIR"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

# autoflush=False: callers must flush/commit explicitly before intra-session queries.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
