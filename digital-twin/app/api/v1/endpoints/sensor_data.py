from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta, timezone
from typing import List

from app.api.v1 import schemas
from app.services import sensor_registry
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/generate", response_model=schemas.SensorDataResponse)
async def generate_sensor_data(
    sensorName: str = Query(..., example="furnace_1_temperature"),
    startDate: datetime = Query(..., example="2025-05-10T08:00:00Z"),
    endDate: datetime = Query(..., example="2025-05-10T09:00:00Z"),
):
    """
    Generates sensor data for a given sensor name over a specified time period.
    Data is generated at a 1-minute interval.
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


    generator_func = sensor_registry.get_generator_function(sensorName)

    if not generator_func:
        raise HTTPException(
            status_code=404,
            detail=f"No generator found for sensor name: {sensorName}",
        )

    logger.info(
        f"Generating data for '{sensorName}' from {startDate} to {endDate}"
    )

    data_points: List[schemas.DataPoint] = []
    current_time = startDate

    while current_time <= endDate:
        # Ensure current_time is also UTC for the generator
        aware_current_time = current_time.astimezone(timezone.utc)
        try:
            value = generator_func(aware_current_time)
            data_points.append(
                schemas.DataPoint(timestamp=aware_current_time, value=value)
            )
        except Exception as e:
            logger.error(
                f"Error generating data for {sensorName} at {aware_current_time}: {e}",
                exc_info=True
            )
            # Decide if you want to skip this point or raise an error for the whole request
            # For now, we'll skip and log.
        current_time += timedelta(minutes=1)

    return schemas.SensorDataResponse(sensorName=sensorName, data=data_points)

