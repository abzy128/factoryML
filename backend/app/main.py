from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.v1.endpoints import timeseries as timeseries_v1_router
from app.core.config import settings
from app.db.session import init_db # Import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Application startup...")
    await init_db() # Initialize database, create table and hypertable
    print("Database initialized.")
    yield
    # Shutdown
    print("Application shutdown...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A gateway for retrieving time-series data from various manufacturing facility sensors, with TimescaleDB backend.",
    lifespan=lifespan # Add lifespan context manager
)

app.include_router(
    timeseries_v1_router.router,
    prefix="/api/v1/timeseries",
    tags=["Time-Series Data v1"],
)

@app.get("/", tags=["Root"])
async def read_root():
    return {
        "message": f"Welcome to {settings.APP_NAME} v{settings.APP_VERSION}"
    }
