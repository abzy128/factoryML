from fastapi import APIRouter, HTTPException, Query, Depends, Path
from datetime import datetime, timedelta, timezone
import httpx
import asyncio
from typing import List, Dict, Set

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.timeseries_schemas import (
    CombinedSensorDataResponse,
    CombinedDataPoint,
    DataPoint as SourceDataPoint, # From external APIs
)
from app.services.digital_twin_client import (
    DigitalTwinAPIClient, get_digital_twin_api_client,
    DigitalTwinAPIError # Catch specific errors
)
from app.services.prediction_model_client import (
    PredictionModelAPIClient, get_prediction_model_api_client,
    PredictionAPIError # Catch specific errors
)
from app.db.session import get_async_db
from app.crud.crud_sensor_data import (
    get_sensor_data_from_db, 
    upsert_sensor_data_points_db,
    truncate_to_minute
)


router = APIRouter()

async def get_http_client():
    async with httpx.AsyncClient() as client:
        yield client

def generate_expected_timestamps(start_dt: datetime, end_dt: datetime) -> Set[datetime]:
    expected_ts = set()
    current_ts = truncate_to_minute(start_dt)
    final_ts = truncate_to_minute(end_dt)
    while current_ts <= final_ts:
        expected_ts.add(current_ts)
        current_ts += timedelta(minutes=1)
    return expected_ts

@router.get(
    "/{sensor_name}",
    response_model=CombinedSensorDataResponse,
    summary="Get combined real and predicted time-series data for a sensor from DB and APIs",
)
async def get_combined_sensor_data_with_db_endpoint(
    sensor_name: str = Path(..., example="ActivePower"),
    start_date: datetime = Query(..., example="2025-02-17T01:00:00Z"),
    end_date: datetime = Query(..., example="2025-02-17T02:00:00Z"),
    db: AsyncSession = Depends(get_async_db),
    dt_client: DigitalTwinAPIClient = Depends(get_digital_twin_api_client),
    pred_client: PredictionModelAPIClient = Depends(get_prediction_model_api_client),
    http_client: httpx.AsyncClient = Depends(get_http_client),
):
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="endDate must be after startDate")

    # Truncate input dates for consistency
    start_date_trunc = truncate_to_minute(start_date)
    end_date_trunc = truncate_to_minute(end_date)

    # 1. Get existing data from DB
    db_data_list = await get_sensor_data_from_db(db, sensor_name, start_date_trunc, end_date_trunc)
    
    # Convert DB data to a map for easy lookup and modification
    # timestamp -> CombinedDataPoint
    merged_data_map: Dict[datetime, CombinedDataPoint] = {
        dp.timestamp: dp for dp in db_data_list
    }

    # 2. Determine what's missing
    expected_timestamps = generate_expected_timestamps(start_date_trunc, end_date_trunc)
    
    needs_real_fetch = False
    needs_predicted_fetch = False

    for ts in expected_timestamps:
        if ts not in merged_data_map:
            needs_real_fetch = True
            needs_predicted_fetch = True
            continue # No data for this timestamp at all
        
        # Check if real_value is missing
        if merged_data_map[ts].real_value is None:
            needs_real_fetch = True
        
        # Check if predicted_value is missing
        if merged_data_map[ts].predicted_value is None:
            needs_predicted_fetch = True
            
        if needs_real_fetch and needs_predicted_fetch: # Optimization
            break 

    api_error_messages = []

    # 3. Fetch from DigitalTwinAPI if necessary
    if needs_real_fetch:
        try:
            print(f"Fetching real data for {sensor_name} from API...")
            real_api_response = await dt_client.get_sensor_data(
                sensor_name, start_date_trunc, end_date_trunc, http_client
            )
            if real_api_response and real_api_response.data:
                await upsert_sensor_data_points_db(db, sensor_name, real_api_response.data, "real")
                # Update merged_data_map with new real data
                for dp in real_api_response.data:
                    ts_minute = truncate_to_minute(dp.timestamp)
                    if ts_minute not in merged_data_map:
                        merged_data_map[ts_minute] = CombinedDataPoint(timestamp=ts_minute)
                    merged_data_map[ts_minute].real_value = dp.value
            # No commit here, handled by get_async_db dependency manager
        except DigitalTwinAPIError as e:
            msg = f"Failed to fetch or store real data from DigitalTwinAPI: {e.message}"
            print(msg)
            api_error_messages.append(msg)
        except Exception as e: # Catch other unexpected errors during fetch/upsert
            msg = f"Unexpected error processing real data: {str(e)}"
            print(msg)
            api_error_messages.append(msg)


    # 4. Fetch from PredictionModelAPI if necessary
    if needs_predicted_fetch:
        try:
            print(f"Fetching predicted data for {sensor_name} from API...")
            predicted_api_response = await pred_client.get_predicted_data(
                sensor_name, start_date_trunc, end_date_trunc, http_client
            )
            if predicted_api_response and predicted_api_response.data:
                await upsert_sensor_data_points_db(db, sensor_name, predicted_api_response.data, "predicted")
                # Update merged_data_map with new predicted data
                for dp in predicted_api_response.data:
                    ts_minute = truncate_to_minute(dp.timestamp)
                    if ts_minute not in merged_data_map:
                        merged_data_map[ts_minute] = CombinedDataPoint(timestamp=ts_minute)
                    merged_data_map[ts_minute].predicted_value = dp.value
        except PredictionAPIError as e:
            msg = f"Failed to fetch or store predicted data from PredictionModelAPI: {e.message}"
            print(msg)
            api_error_messages.append(msg)
        except Exception as e:
            msg = f"Unexpected error processing predicted data: {str(e)}"
            print(msg)
            api_error_messages.append(msg)
    
    # 5. Construct final response from merged_data_map, ensuring all expected timestamps are present
    final_data_points: List[CombinedDataPoint] = []
    for ts in sorted(list(expected_timestamps)): # Ensure sorted output
        if ts in merged_data_map:
            final_data_points.append(merged_data_map[ts])
        else:
            # This case should ideally be covered if merged_data_map is updated correctly
            # after API fetches. If a timestamp is expected but not in map, it means
            # it wasn't in DB and wasn't fetched (or fetch failed and wasn't added).
            final_data_points.append(CombinedDataPoint(timestamp=ts, real_value=None, predicted_value=None))
            
    response_message = "Data fetched successfully."
    if api_error_messages:
        response_message += " Some API errors occurred: " + "; ".join(api_error_messages)

    return CombinedSensorDataResponse(
        sensorName=sensor_name,
        data=final_data_points,
        message=response_message
    )
