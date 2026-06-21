# File: backend/main.py
"""
Application entrypoint.

WHY: The health check executes a real query so monitoring detects a
dead database, rather than reporting healthy while the DB is down.
The lifespan handler builds the schema on startup via create_all.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.init_db import init_db
from app.api.routes import auth as auth_routes
from app.api.routes import case_extract as case_extract_routes
from app.api.routes import cases as cases_routes
from app.api.routes import clusters as clusters_routes
from app.api.routes import entities as entities_routes
from app.api.routes import evidence as evidence_routes
from app.api.routes import search as search_routes
from app.api.routes import users as users_routes
from app.api.routes import dashboard as dashboard_routes


from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.rate_limit import limiter



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

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth_routes.router)
app.include_router(users_routes.router)
app.include_router(cases_routes.router)
app.include_router(case_extract_routes.router)
app.include_router(entities_routes.router)
app.include_router(search_routes.router)
app.include_router(clusters_routes.router)
app.include_router(evidence_routes.router)
app.include_router(dashboard_routes.router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Liveness + DB connectivity check."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
