# File: backend/main.py
"""
Application entrypoint.

WHY: The health check executes a real query so monitoring detects a
dead database, rather than reporting healthy while the DB is down.
The lifespan handler builds the schema on startup via create_all.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.init_db import init_db
from app.api.routes import auth as auth_routes
from app.api.routes import cases as cases_routes
from app.api.routes import entities as entities_routes
from app.api.routes import evidence as evidence_routes
from app.api.routes import users as users_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build any missing tables before serving requests (idempotent).
    init_db()
    yield


app = FastAPI(
    title="Cyber Investigation Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_routes.router)
app.include_router(users_routes.router)
app.include_router(cases_routes.router)
app.include_router(entities_routes.router)
app.include_router(evidence_routes.router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Liveness + DB connectivity check."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
