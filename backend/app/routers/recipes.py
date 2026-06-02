from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Inventory, Product, Recipe
from app.schemas import RecipeCreate, RecipeOut, RecipeUpdate
from app.security import require_roles

router = APIRouter(prefix="/recipes", tags=["recipes"])

_allowed = require_roles("admin", "manager")


def _to_out(recipe: Recipe, db: Session) -> RecipeOut:
    product = db.query(Product).filter(Product.id == recipe.product_id).first()
    ingredient = db.query(Inventory).filter(Inventory.id == recipe.ingredient_id).first()
    return RecipeOut(
        id=recipe.id,
        product_id=recipe.product_id,
        product_name=product.name if product else "",
        ingredient_id=recipe.ingredient_id,
        ingredient_name=ingredient.name if ingredient else "",
        qty=recipe.qty,
    )


@router.get("", response_model=List[RecipeOut])
def list_recipes(
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    query = db.query(Recipe)
    if product_id is not None:
        query = query.filter(Recipe.product_id == product_id)
    recipes = (
        query.join(Product, Recipe.product_id == Product.id)
        .order_by(Product.name)
        .all()
    )
    return [_to_out(r, db) for r in recipes]


@router.post("", response_model=RecipeOut, status_code=201)
def create_recipe(
    body: RecipeCreate,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    product = db.query(Product).filter(Product.id == body.product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    ingredient = db.query(Inventory).filter(Inventory.id == body.ingredient_id).first()
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    recipe = Recipe(
        product_id=body.product_id,
        ingredient_id=body.ingredient_id,
        qty=body.qty,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return _to_out(recipe, db)


@router.patch("/{recipe_id}", response_model=RecipeOut)
def update_recipe(
    recipe_id: int,
    body: RecipeUpdate,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    recipe.qty = body.qty
    db.commit()
    db.refresh(recipe)
    return _to_out(recipe, db)


@router.delete("/{recipe_id}", status_code=200)
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    db.delete(recipe)
    db.commit()
    return {"detail": "Deleted"}
