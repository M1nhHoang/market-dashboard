"""
FastAPI Application - Market Intelligence Dashboard API
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import ensure_directories
from database import init_engine
from database.init import run_migrations
from utils import logger, init_logging
from .routes import router

# Run migrations BEFORE app starts (outside async context)
init_logging(app_name="api")
ensure_directories()

try:
    run_migrations()
except Exception as e:
    logger.error(f"Migration failed: {e}")
    # Don't raise - let the app start anyway, migrations may have already been applied


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting API server")
    
    await init_engine()
    yield
    # Shutdown
    logger.info("Shutting down API server")


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
