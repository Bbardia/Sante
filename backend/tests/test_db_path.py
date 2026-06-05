"""Unit tests for app.db.resolve_db_path.

The packaged app must keep its SQLite database in a writable, persistent
per-user directory (passed via SANTE_DATA_DIR). In development, with no env
var set, it must fall back to the repo-local backend/database.db.
"""

from pathlib import Path

import app.db as dbmod
from app.db import resolve_db_path


def _default_dev_path() -> Path:
    # app/db.py -> parent is app/, parent.parent is backend/
    return Path(dbmod.__file__).resolve().parent.parent / "database.db"


def test_uses_data_dir_when_set(tmp_path):
    result = resolve_db_path(str(tmp_path))
    assert result == tmp_path / "database.db"


def test_falls_back_to_dev_path_when_none():
    assert resolve_db_path(None) == _default_dev_path()


def test_empty_string_is_treated_as_unset():
    # An env var set to "" should not produce Path("")/database.db.
    assert resolve_db_path("") == _default_dev_path()
