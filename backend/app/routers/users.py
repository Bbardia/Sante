from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate
from app.security import hash_password, require_roles

router = APIRouter(prefix="/users", tags=["users"])

_admin_only = require_roles("admin")


@router.get("", response_model=List[UserOut])
def list_users(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(_admin_only),
):
    query = db.query(User)
    if search:
        query = query.filter(User.username.contains(search))
    return query.all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(_admin_only),
):
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already exists")
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(_admin_only),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if body.username is not None:
        # Check for clash with another user
        clash = (
            db.query(User)
            .filter(User.username == body.username, User.id != user_id)
            .first()
        )
        if clash:
            raise HTTPException(status_code=409, detail="Username already taken")
        user.username = body.username

    if body.password is not None:
        user.password_hash = hash_password(body.password)

    if body.role is not None:
        user.role = body.role

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=200)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(_admin_only),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete the admin user")
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}
