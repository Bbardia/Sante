"""Backup and restore endpoints.

GET  /backup  – download the current SQLite database file.
POST /restore – upload a SQLite file to replace the current database.

Both endpoints are restricted to admin and manager roles.

Design note: DB_PATH and engine are accessed through the module object at
call-time (``import app.db as dbmod``) so tests can monkeypatch them without
binding stale values at import.
"""

from datetime import datetime

import app.db as dbmod
from app.security import require_roles

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

router = APIRouter(tags=["backup"])

_SQLITE_MAGIC = b"SQLite format 3\x00"

_admin_or_manager = require_roles("admin", "manager")


@router.get("/backup")
async def download_backup(
    _=Depends(_admin_or_manager),
):
    """Download the current SQLite database as a binary file."""
    db_path = dbmod.DB_PATH
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database file not found")
    return FileResponse(
        str(db_path),
        media_type="application/octet-stream",
        filename="sante-backup.db",
    )


@router.post("/restore")
async def restore_backup(
    file: UploadFile,
    _=Depends(_admin_or_manager),
):
    """Replace the current database with an uploaded SQLite file.

    Steps:
    1. Validate the uploaded file is a SQLite database.
    2. Create a timestamped safety backup of the existing database.
    3. Dispose of open engine connections.
    4. Overwrite the database file with the uploaded content.
    """
    content = await file.read()

    # Validate SQLite magic bytes
    if not content.startswith(_SQLITE_MAGIC):
        raise HTTPException(status_code=400, detail="Not a valid SQLite database")

    db_path = dbmod.DB_PATH
    backups_dir = db_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    safety_backup: str | None = None

    # Create a safety backup of the current DB if it exists
    if db_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"sante-pre-restore-{timestamp}.db"
        backup_path = backups_dir / backup_name
        backup_path.write_bytes(db_path.read_bytes())
        safety_backup = backup_name

    # Release all open SQLAlchemy connections before overwriting
    dbmod.engine.dispose()

    # Write the new database
    db_path.write_bytes(content)

    return {"restored": True, "safety_backup": safety_backup}
