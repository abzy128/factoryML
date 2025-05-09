from fastapi import FastAPI
import logging
from contextlib import asynccontextmanager

from app.api.v1.endpoints import sensor_data as sensor_data_router_v1
from app.services import sensor_registry # Import to trigger loading

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application startup...")
    # Trigger loading of generators if not already done (it should be by import)
    if not sensor_registry.GENERATOR_REGISTRY:
        sensor_registry._load_generators()
    logger.info(f"Loaded {len(sensor_registry.GENERATOR_REGISTRY)} generator patterns.")
    yield
    # Shutdown
    logger.info("Application shutdown...")


app = FastAPI(
    title="IoT Sensor Data Generator",
    description="Generates mock IoT sensor data based on sensor name and time period.",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(
    sensor_data_router_v1.router,
    prefix="/api/v1/sensordata",
    tags=["Sensor Data Generation"],
)

@app.get("/", tags=["Root"])
async def read_root():
    return {
        "message": "Welcome to the IoT Sensor Data Generator API. See /docs for details."
    }

# For running directly (though uvicorn CLI is preferred)
# import uvicorn
# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8001)

