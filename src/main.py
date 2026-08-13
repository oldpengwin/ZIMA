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
from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.middleware import SlowAPIMiddleware  # noqa: E402
from slowapi.util import get_remote_address  # noqa: E402

from src.api.routes import router as api_router  # noqa: E402
from src.core.config import get_settings  # noqa: E402

settings = get_settings()

# Global per-IP rate limit, values from config. Enforced in production only, so
# local runs and the test suite (which fire many requests from one client IP)
# aren't throttled. Flip ENVIRONMENT=production to exercise it.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_requests} per {settings.rate_limit_window_minutes} minutes"],
    enabled=settings.is_production,
)

# Swagger/OpenAPI are exposed only outside production — no need to publish the
# full API surface (and its schema) on a live deployment.
app = FastAPI(
    title="ZIMA Platform API",
    description="RESTful API for the ZIMA community platform with neurotype-based matching",
    version="1.0.0",
    docs_url=None if settings.is_production else "/api/docs",
    redoc_url=None if settings.is_production else "/api/redoc",
    openapi_url=None if settings.is_production else "/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in settings.allowed_origins if o] or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

_FRONTEND_BUILD_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if settings.is_production and os.path.isdir(_FRONTEND_BUILD_DIR):
    # Optional third deployment path — the two documented ones (src/frontend/README.md)
    # are a separate static host (Vercel/Netlify/...) or the nginx container in
    # Dockerfile.frontend; this lets the API container also serve the frontend
    # directly if its build output happens to be present alongside it. Was
    # "frontend/build": (1) cwd-independent via os.path.dirname(__file__), which
    # was already correct, but (2) still named the wrong directory — Vite (what
    # actually gets built, not the old CRA scaffold) outputs to "dist", not
    # "build". Since Dockerfile.backend never COPYs a frontend build into the
    # image, os.path.isdir() was always False and this silently no-op'd either
    # way — fixed for correctness so it actually works for anyone who wires up
    # that combined-container path (13-Aug-2026 production audit).
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
