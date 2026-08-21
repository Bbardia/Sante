from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 – registers all ORM models with Base
from app.db import SessionLocal, engine, Base
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.inventory import router as inventory_router
from app.routers.products import router as products_router
from app.routers.recipes import router as recipes_router
from app.routers.customers import router as customers_router
from app.routers.sales import router as sales_router
from app.routers.debts import router as debts_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create tables if they don't exist yet
    Base.metadata.create_all(bind=engine)

    # Seed: ensure at least one admin user exists
    from app.models import User
    from app.security import hash_password

    with SessionLocal() as db:
        if not db.query(User).first():
            db.add(User(username="admin", password_hash=hash_password("admin"), role="admin"))
            db.commit()

    yield


app = FastAPI(title="Santé API", lifespan=lifespan)

# Dev CORS: allow the Vite dev server. Tightened in a later phase.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(inventory_router)
app.include_router(products_router)
app.include_router(recipes_router)
app.include_router(customers_router)
app.include_router(sales_router)
app.include_router(debts_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
