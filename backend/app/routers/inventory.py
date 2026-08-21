from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Inventory, Recipe
from app.schemas import InventoryAdd, InventoryOut, InventoryUpdate
from app.security import require_roles

router = APIRouter(prefix="/inventory", tags=["inventory"])

_allowed = require_roles("admin", "manager", "stockman")


def _to_out(obj: Inventory) -> InventoryOut:
    return InventoryOut.from_orm_obj(obj)


@router.get("", response_model=List[InventoryOut])
def list_inventory(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    query = db.query(Inventory)
    if search:
        query = query.filter(Inventory.name.contains(search))
    items = query.order_by(Inventory.name).all()
    return [_to_out(item) for item in items]


@router.post("", response_model=InventoryOut, status_code=201)
def add_stock(
    body: InventoryAdd,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    existing = (
        db.query(Inventory)
        .filter(func.lower(Inventory.name) == body.name.lower())
        .first()
    )
    if existing:
        existing.qty += body.qty
        existing.total_value += body.qty * body.price
        existing.unit = body.unit
        if body.reorder_level is not None:
            existing.reorder_level = body.reorder_level
        db.commit()
        db.refresh(existing)
        return _to_out(existing)
    else:
        item = Inventory(
            name=body.name,
            qty=body.qty,
            unit=body.unit,
            total_value=body.qty * body.price,
            reorder_level=body.reorder_level if body.reorder_level is not None else 0.0,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return _to_out(item)


@router.patch("/{item_id}", response_model=InventoryOut)
def update_inventory(
    item_id: int,
    body: InventoryUpdate,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if body.name is not None:
        clash = (
            db.query(Inventory)
            .filter(
                func.lower(Inventory.name) == body.name.lower(),
                Inventory.id != item_id,
            )
            .first()
        )
        if clash:
            raise HTTPException(status_code=409, detail="Name already exists")
        item.name = body.name

    if body.unit is not None:
        item.unit = body.unit

    if body.reorder_level is not None:
        item.reorder_level = body.reorder_level

    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.delete("/{item_id}", status_code=200)
def delete_inventory(
    item_id: int,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    # Delete related recipe rows first
    db.query(Recipe).filter(Recipe.ingredient_id == item_id).delete()
    db.delete(item)
    db.commit()
    return {"detail": "Deleted"}


@router.post("/reset", status_code=200)
def reset_inventory(
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    count = db.query(Inventory).count()
    db.query(Inventory).update({"qty": 0, "total_value": 0})
    db.commit()
    return {"reset": count}
