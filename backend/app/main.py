from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from app.api.v1.endpoints import data as data_router_v1
from app.db.session import init_db, engine # Import engine for disposal
from app.core.config import settings # To access settings if needed

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application startup...")
    logger.info(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1]}") # Mask credentials
    logger.info(f"IoT Host: {settings.IOT_HOST}")
    logger.info(f"ML Host: {settings.ML_HOST}")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        # Depending on severity, you might want to prevent app startup
        # For now, we log and continue, but DB operations might fail.
    yield
    # Shutdown
    logger.info("Application shutdown...")
    await engine.dispose() # Properly close the connection pool
    logger.info("Database connection pool closed.")


app = FastAPI(
    title="TimescaleDB Data Service",
    description="API for fetching real and predicted time-series data, with TimescaleDB backend.",
    version="0.1.0",
    lifespan=lifespan
)

# Include routers
app.include_router(data_router_v1.router, prefix="/api/v1/data", tags=["Time Series Data"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the TimescaleDB Data Service API. See /docs for details."}

# If you want to run this directly with `python app/main.py` (though uvicorn is preferred)
# import uvicorn
# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)

