from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Product, Recipe
from app.schemas import ProductCreate, ProductOut, ProductUpdate
from app.security import require_roles

router = APIRouter(prefix="/products", tags=["products"])

_allowed = require_roles("admin", "manager")


@router.get("", response_model=List[ProductOut])
def list_products(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    query = db.query(Product)
    if search:
        query = query.filter(Product.name.contains(search))
    return query.order_by(Product.name).all()


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    existing = db.query(Product).filter(Product.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Product name already exists")
    product = Product(name=body.name, price=body.price)
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Product name already exists")
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if body.name is not None:
        clash = (
            db.query(Product)
            .filter(Product.name == body.name, Product.id != product_id)
            .first()
        )
        if clash:
            raise HTTPException(status_code=409, detail="Product name already taken")
        product.name = body.name

    if body.price is not None:
        product.price = body.price

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Product name already taken")
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=200)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Delete related recipe rows first
    db.query(Recipe).filter(Recipe.product_id == product_id).delete()
    db.delete(product)
    db.commit()
    return {"detail": "Deleted"}
