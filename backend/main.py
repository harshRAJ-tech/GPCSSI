# File: backend/main.py
"""
Application entrypoint.

WHY: The health check executes a real query so monitoring detects a
dead database, rather than reporting healthy while the DB is down.
"""
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

app = FastAPI(title="Cyber Investigation Intelligence Platform", version="0.1.0")


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Liveness + DB connectivity check."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
