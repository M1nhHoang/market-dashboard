"""
FastAPI Application - Market Intelligence Dashboard API
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings, ensure_directories
from database import init_database_async, init_engine
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    ensure_directories()
    await init_engine()  # Initialize DB engine
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Market Intelligence Dashboard",
    description="API for Vietnam and Global macro/financial news analysis",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Market Intelligence Dashboard",
        "version": "1.0.0",
        "status": "running"
    }
