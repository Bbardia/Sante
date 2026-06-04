from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Inventory, Product, Recipe
from app.schemas import RecipeCreate, RecipeOut, RecipeSet, RecipeUpdate
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


@router.put("/product/{product_id}", response_model=List[RecipeOut])
def set_product_recipe(
    product_id: int,
    body: RecipeSet,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    """Replace the entire recipe for a product in one atomic call."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate all items before any mutation
    seen_ingredient_ids: set[int] = set()
    for item in body.items:
        if item.qty <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
        if item.ingredient_id in seen_ingredient_ids:
            raise HTTPException(status_code=400, detail="Duplicate ingredient in recipe")
        seen_ingredient_ids.add(item.ingredient_id)
        ingredient = db.query(Inventory).filter(Inventory.id == item.ingredient_id).first()
        if ingredient is None:
            raise HTTPException(status_code=404, detail=f"Ingredient {item.ingredient_id} not found")

    # Delete all existing recipe rows for this product
    db.query(Recipe).filter(Recipe.product_id == product_id).delete()

    # Insert new rows
    new_recipes = []
    for item in body.items:
        recipe = Recipe(product_id=product_id, ingredient_id=item.ingredient_id, qty=item.qty)
        db.add(recipe)
        new_recipes.append(recipe)

    db.commit()
    for recipe in new_recipes:
        db.refresh(recipe)

    return [_to_out(r, db) for r in new_recipes]


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
