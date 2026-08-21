from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from app.security import VALID_ROLES

# ---------------------------------------------------------------------------
# Inventory schemas
# ---------------------------------------------------------------------------


class InventoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    qty: float
    unit: str
    total_value: float
    avg_price: float
    reorder_level: float

    @classmethod
    def from_orm_obj(cls, obj) -> "InventoryOut":
        avg_price = round(obj.total_value / obj.qty, 2) if obj.qty > 0 else 0.0
        return cls(
            id=obj.id,
            name=obj.name,
            qty=obj.qty,
            unit=obj.unit,
            total_value=obj.total_value,
            avg_price=avg_price,
            reorder_level=obj.reorder_level,
        )


class InventoryAdd(BaseModel):
    name: str
    qty: float
    unit: str
    price: float
    reorder_level: float | None = None


class InventoryUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    reorder_level: float | None = None


# ---------------------------------------------------------------------------
# Product schemas
# ---------------------------------------------------------------------------


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float


class ProductCreate(BaseModel):
    name: str
    price: float


class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = None


# ---------------------------------------------------------------------------
# Recipe schemas
# ---------------------------------------------------------------------------


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    ingredient_id: int
    ingredient_name: str
    qty: float


class RecipeCreate(BaseModel):
    product_id: int
    ingredient_id: int
    qty: float


class RecipeUpdate(BaseModel):
    qty: float


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
