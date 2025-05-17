from fastapi import FastAPI
import logging

from app.api.v1.endpoints import sensor_data as sensor_data_router_v1

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sensor Data API",
    description="Fetches time-series data",
    version="0.1.0"
)

app.include_router(
    sensor_data_router_v1.router,
    prefix="/api/v1/sensor/data",
    tags=["Sensor Data"],
)

@app.get("/", tags=["Root"])
async def read_root():
    return {
        "message": "Welcome to the Digital Twin API. See /docs for details."
    }

# For running directly (though uvicorn CLI is preferred)
# import uvicorn
# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8001)

