"""
Shared test fixtures.

Uses a per-test SQLite file in a temp directory so tests never touch the dev
database.db and always start from a clean slate.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app as fastapi_app


@pytest.fixture()
def client(tmp_path):
    """Yield a TestClient backed by a fresh, in-memory SQLite database.

    Dependency override ensures every request in this fixture's test uses the
    test DB, not the production one.
    """
    db_path = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    # Create all tables on the test engine (imports models as a side-effect)
    import app.models  # noqa: F401 – registers User table with Base

    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db

    # Seed the admin user exactly as the lifespan handler does in production
    from app.models import User
    from app.security import hash_password

    with TestingSessionLocal() as seed_db:
        if not seed_db.query(User).first():
            seed_db.add(User(username="admin", password_hash=hash_password("admin"), role="admin"))
            seed_db.commit()

    with TestClient(fastapi_app) as c:
        yield c

    # Clean up overrides so other tests (e.g. test_health) are unaffected
    fastapi_app.dependency_overrides.pop(get_db, None)
