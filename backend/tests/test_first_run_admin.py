"""Tests for first-run admin password selection."""

from app.main import DEFAULT_ADMIN_PASSWORD, get_initial_admin_password


def test_initial_admin_password_generates_random_password_by_default(monkeypatch):
    monkeypatch.delenv("SANTE_INITIAL_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("SANTE_DEMO_ADMIN", raising=False)

    password = get_initial_admin_password()

    assert password != DEFAULT_ADMIN_PASSWORD
    assert len(password) >= 20


def test_initial_admin_password_can_come_from_environment(monkeypatch):
    monkeypatch.setenv("SANTE_INITIAL_ADMIN_PASSWORD", "change-me-on-first-run")
    monkeypatch.delenv("SANTE_DEMO_ADMIN", raising=False)

    assert get_initial_admin_password() == "change-me-on-first-run"


def test_demo_admin_password_requires_explicit_demo_flag(monkeypatch):
    monkeypatch.delenv("SANTE_INITIAL_ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("SANTE_DEMO_ADMIN", "1")

    assert get_initial_admin_password() == DEFAULT_ADMIN_PASSWORD
