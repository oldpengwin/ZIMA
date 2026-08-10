"""
ZIMA Platform - FastAPI Main Application

This is the main entry point for the ZIMA backend API.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import router as api_router

# Create FastAPI app
app = FastAPI(
    title="ZIMA Platform API",
    description="RESTful API for the ZIMA community platform with neurotype-based matching",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        os.getenv("FRONTEND_URL", "")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)

# Mount static files (for production frontend)
if os.getenv("NODE_ENV") == "production":
    app.mount("/", StaticFiles(directory="frontend/build", html=True), name="frontend")

@app.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "service": "zima-api",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """
    Root endpoint

    Returns:
        dict: Welcome message
    """
    return {
        "message": "Welcome to ZIMA Platform API",
        "docs": "/api/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
