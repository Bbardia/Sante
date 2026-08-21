"""Tests for the global catch-all exception handler.

Verifies that:
- An unhandled RuntimeError produces a clean 500 JSON response with no
  internal details leaked.
- FastAPI's built-in HTTPException handling is untouched (intentional 4xx
  errors still come through as-is).
- The /health endpoint still returns 200.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BOOM_ROUTE = "/__boom_test_only"


def _raise_runtime_error():
    raise RuntimeError("boom — internal details must NOT leak to client")


# Register a throwaway route that always raises an unhandled exception.
# We add it directly to the app instance (same object used by every test),
# but the route path is obscure enough not to clash with any real endpoint.
app.add_api_route(_BOOM_ROUTE, _raise_runtime_error, methods=["GET"])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unhandled_exception_returns_clean_500():
    """Unhandled RuntimeError must produce 500 + {detail: 'Internal server error'}."""
    # raise_server_exceptions=False: let the handler return its JSONResponse
    # instead of propagating the exception into the test process.
    c = TestClient(app, raise_server_exceptions=False)
    resp = c.get(_BOOM_ROUTE)
    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal server error"}


def test_no_internal_details_in_response():
    """The raw exception message must NOT appear in the response body."""
    c = TestClient(app, raise_server_exceptions=False)
    resp = c.get(_BOOM_ROUTE)
    assert "boom" not in resp.text
    assert "RuntimeError" not in resp.text
    assert "Traceback" not in resp.text


def test_health_unaffected():
    """GET /health must still return 200 — catch-all must not swallow normal routes."""
    c = TestClient(app, raise_server_exceptions=False)
    resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_http_exception_unauthenticated_not_swallowed(client):
    """GET /auth/me without a token should still return 401/403, not 500."""
    resp = client.get("/auth/me")
    assert resp.status_code in (401, 403)


def test_http_exception_forbidden_not_swallowed(client):
    """GET /users without a token should still return 401/403, not 500."""
    resp = client.get("/users")
    assert resp.status_code in (401, 403)
