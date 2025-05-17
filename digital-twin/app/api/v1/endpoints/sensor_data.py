from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from app.api.v1 import schemas
from app.services.sensor_data_repo import SensorDataRepo
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

CSV_PATH = "../data/dataset.csv"

@router.get("/api/v1/sensor/data", response_model=schemas.SensorDataResponse)
async def get_sensor_data(
    sensorName: str = Query(..., example="ActivePower"),
    startDate: datetime = Query(..., example="2025-01-25T08:00:00Z"),
    endDate: datetime = Query(..., example="2025-01-25T09:00:00Z"),
):
    """
    Fetches time-series data for a specific sensor between two dates.
    Data is returned at a 1-minute interval.
    """
    if startDate >= endDate:
        raise HTTPException(
            status_code=400, detail="startDate must be before endDate"
        )

    # Ensure datetimes are timezone-aware (UTC is good practice)
    if startDate.tzinfo is None:
        startDate = startDate.replace(tzinfo=timezone.utc)
    if endDate.tzinfo is None:
        endDate = endDate.replace(tzinfo=timezone.utc)

    retriever = SensorDataRepo(CSV_PATH)

    data_points = retriever.get_sensor_value(sensorName, startDate, endDate)

    return schemas.SensorDataResponse(sensorName=sensorName, data=data_points)
