"""Unit tests for app/security.py utilities."""

from app.security import hash_password, verify_password, create_access_token, decode_token


def test_hash_is_not_plaintext():
    h = hash_password("supersecret")
    assert h != "supersecret"


def test_verify_correct_password():
    h = hash_password("correct")
    assert verify_password("correct", h) is True


def test_verify_wrong_password():
    h = hash_password("correct")
    assert verify_password("wrong", h) is False


def test_decode_token_roundtrip():
    token = create_access_token("alice", "admin")
    payload = decode_token(token)
    assert payload["sub"] == "alice"
    assert payload["role"] == "admin"
