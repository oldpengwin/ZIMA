"""
ZIMA Platform - FastAPI Main Application

Main entry point for the ZIMA backend API. Config is validated at import
time (src/core/config.py raises loudly in production if anything required
is missing) rather than discovered as a runtime 500 later.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()  # must happen before core.config reads os.environ

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from src.api.routes import router as api_router  # noqa: E402
from src.core.config import get_settings  # noqa: E402

settings = get_settings()

app = FastAPI(
    title="ZIMA Platform API",
    description="RESTful API for the ZIMA community platform with neurotype-based matching",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in settings.allowed_origins if o] or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

_FRONTEND_BUILD_DIR = os.path.join(os.path.dirname(__file__), "frontend", "build")
if settings.is_production and os.path.isdir(_FRONTEND_BUILD_DIR):
    # Was "frontend/build" — a path that only resolves correctly if the process's cwd happens
    # to be the repo root AND a top-level frontend/ directory exists, neither of which is true
    # here (the frontend lives at src/frontend/, and Dockerfile.backend's WORKDIR is /app with
    # cwd-independent execution via gunicorn). This never crashed — os.path.isdir() just quietly
    # returned False and skipped mounting — so it would have shipped as a silent no-op the first
    # time someone actually tried to serve the frontend from the API container.
    app.mount("/", StaticFiles(directory=_FRONTEND_BUILD_DIR, html=True), name="frontend")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "zima-api", "version": "1.0.0", "environment": settings.environment}


@app.get("/")
async def root():
    return {"message": "Welcome to ZIMA Platform API", "docs": "/api/docs", "health": "/health"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=not settings.is_production,
        log_level="info",
    )
