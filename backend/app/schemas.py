from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from app.security import VALID_ROLES


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
        return v


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role: str | None = None

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
        return v
