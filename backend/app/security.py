import os
from typing import Callable

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET = os.environ.get("SANTE_SECRET", "dev-secret-change-me")
ALGORITHM = "HS256"

VALID_ROLES = {"admin", "manager", "salesman", "stockman"}

_bearer_scheme = HTTPBearer()


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(username: str, role: str) -> str:
    payload = {"sub": username, "role": role}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and return the JWT payload. Raises jwt.PyJWTError on invalid tokens."""
    return jwt.decode(token, SECRET, algorithms=[ALGORITHM])


def get_current_user(
    creds=Depends(_bearer_scheme),
    db: Session = Depends(get_db),
):
    """FastAPI dependency: decode the Bearer token and return the matching User."""
    from app.models import User  # local import to avoid circular at module load

    try:
        payload = decode_token(creds.credentials)
        username: str = payload.get("sub", "")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_roles(*roles: str) -> Callable:
    """Return a FastAPI dependency that enforces role membership."""

    def dependency(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return dependency
