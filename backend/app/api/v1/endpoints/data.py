from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import List

from app.db.session import get_db
from app.api.v1 import schemas
from app.crud import crud_timeseries
from app.services import iot_service, ml_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

async def _get_or_fetch_data(
    db: AsyncSession,
    source_type: str,
    start_time: datetime,
    end_time: datetime,
    fetch_function: callable
) -> List[schemas.DataPoint]:
    """Helper function to reduce redundancy in endpoint logic."""
    # 1. Check database first
    db_data_dicts = await crud_timeseries.get_data_by_source_and_time_range(
        db, source=source_type, start_time=start_time, end_time=end_time
    )

    # Convert list of dicts from DB to list of DataPoint Pydantic models
    db_data_points = [schemas.DataPoint(**row) for row in db_data_dicts]


    # 2. If no data (or insufficient data - for now, just checking if empty), fetch from external service
    # A more complex logic could check if the number of points is as expected for the interval.
    if not db_data_points:
        logger.info(f"No '{source_type}' data found in DB for {start_time}-{end_time}. Fetching externally.")
        external_data_to_create: List[schemas.DataPointCreate] = await fetch_function(start_time, end_time)

        if external_data_to_create:
            # 3. Store fetched data in TimescaleDB
            # The bulk_insert function handles ON CONFLICT DO NOTHING
            await crud_timeseries.bulk_insert_data_points(
                db, data_points=external_data_to_create, source=source_type
            )
            logger.info(f"Stored {len(external_data_to_create)} new '{source_type}' data points in DB.")

            # 4. Re-query the database to return the newly inserted data (ensures consistency)
            #    or transform external_data_to_create to DataPoint and return.
            #    Re-querying is safer.
            final_data_dicts = await crud_timeseries.get_data_by_source_and_time_range(
                db, source=source_type, start_time=start_time, end_time=end_time
            )
            return [schemas.DataPoint(**row) for row in final_data_dicts]
        else:
            logger.info(f"External service for '{source_type}' returned no data for {start_time}-{end_time}.")
            return [] # External service returned nothing
    else:
        logger.info(f"Found {len(db_data_points)} '{source_type}' data points in DB for {start_time}-{end_time}.")
        return db_data_points


@router.get("/real", response_model=schemas.DataResponse)
async def get_real_data(
    startTime: datetime = Query(..., description="Start of the time period (ISO 8601 format)"),
    endTime: datetime = Query(..., description="End of the time period (ISO 8601 format)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves real data values for a specified time period.
    If data is not found in the database, it's fetched from the IoT digital twin service and stored.
    """
    if startTime >= endTime:
        raise HTTPException(status_code=400, detail="startTime must be before endTime")

    try:
        data_points = await _get_or_fetch_data(
            db,
            source_type="real",
            start_time=startTime,
            end_time=endTime,
            fetch_function=iot_service.fetch_real_data_from_iot_twin
        )
        return schemas.DataResponse(data=data_points, message="Real data retrieved successfully.")
    except Exception as e:
        logger.error(f"Error in /real endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


@router.get("/predicted", response_model=schemas.DataResponse)
async def get_predicted_data(
    startTime: datetime = Query(..., description="Start of the time period (ISO 8601 format)"),
    endTime: datetime = Query(..., description="End of the time period (ISO 8601 format)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves predicted data values for a specified time period.
    If data is not found in the database, it's fetched from the ML model service and stored.
    """
    if startTime >= endTime:
        raise HTTPException(status_code=400, detail="startTime must be before endTime")

    try:
        data_points = await _get_or_fetch_data(
            db,
            source_type="predicted",
            start_time=startTime,
            end_time=endTime,
            fetch_function=ml_service.fetch_predicted_data_from_ml_model
        )
        return schemas.DataResponse(data=data_points, message="Predicted data retrieved successfully.")
    except Exception as e:
        logger.error(f"Error in /predicted endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


