from fastapi import FastAPI
from app.api.v1.endpoints import timeseries as timeseries_v1_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A gateway for retrieving time-series data from various manufacturing facility sensors.",
)

# Include the v1 timeseries router
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

# To run the application (e.g., from the timeseries_gateway directory):
# uvicorn app.main:app --reload
