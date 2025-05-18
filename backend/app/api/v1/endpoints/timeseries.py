from fastapi import APIRouter, HTTPException, Query, Depends, Path
from datetime import datetime
import httpx
import asyncio # For concurrent API calls

from app.api.v1.schemas.timeseries_schemas import (
    CombinedSensorDataResponse, # New response model
    CombinedDataPoint,
    DataPoint as SourceDataPoint, # To distinguish from CombinedDataPoint
)
from app.services.digital_twin_client import (
    DigitalTwinAPIClient,
    DigitalTwinAPIConnectionError,
    DigitalTwinAPIHttpError,
    DigitalTwinAPIDataValidationError,
    DigitalTwinAPIError,
    get_digital_twin_api_client,
)
from app.services.prediction_model_client import ( # Import new client
    PredictionModelAPIClient,
    PredictionAPIConnectionError,
    PredictionAPIHttpError,
    PredictionAPIDataValidationError,
    PredictionAPIError,
    get_prediction_model_api_client,
)

router = APIRouter()

async def get_http_client():
    async with httpx.AsyncClient() as client:
        yield client

def merge_sensor_data(
    sensor_name: str,
    real_data_points: list[SourceDataPoint],
    predicted_data_points: list[SourceDataPoint],
) -> CombinedSensorDataResponse:
    
    merged_data_map: dict[datetime, CombinedDataPoint] = {}

    for dp in real_data_points:
        if dp.timestamp not in merged_data_map:
            merged_data_map[dp.timestamp] = CombinedDataPoint(timestamp=dp.timestamp)
        merged_data_map[dp.timestamp].real_value = dp.value

    for dp in predicted_data_points:
        if dp.timestamp not in merged_data_map:
            merged_data_map[dp.timestamp] = CombinedDataPoint(timestamp=dp.timestamp)
        merged_data_map[dp.timestamp].predicted_value = dp.value
    
    # Sort by timestamp
    sorted_combined_data = sorted(merged_data_map.values(), key=lambda x: x.timestamp)
    
    return CombinedSensorDataResponse(
        sensorName=sensor_name,
        data=sorted_combined_data,
        message="Data fetched and combined successfully"
    )

@router.get(
    "/{sensor_name}",
    response_model=CombinedSensorDataResponse, # Updated response model
    summary="Get combined real and predicted time-series data for a sensor",
)
async def get_combined_sensor_data_endpoint( # Renamed for clarity
    sensor_name: str = Path(
        ..., description="Name of the sensor", example="ActivePower"
    ),
    start_date: datetime = Query(
        ...,
        description="Start date (ISO 8601 format, e.g., 2025-01-25T08:00:00Z)",
        example="2025-01-25T08:00:00Z",
    ),
    end_date: datetime = Query(
        ...,
        description="End date (ISO 8601 format, e.g., 2025-01-25T09:00:00Z)",
        example="2025-01-25T09:00:00Z",
    ),
    dt_client: DigitalTwinAPIClient = Depends(get_digital_twin_api_client),
    pred_client: PredictionModelAPIClient = Depends(get_prediction_model_api_client),
    http_client: httpx.AsyncClient = Depends(get_http_client),
):
    if start_date >= end_date:
        raise HTTPException(
            status_code=400, detail="endDate must be after startDate"
        )

    # Fetch data from both services concurrently
    real_data_task = dt_client.get_sensor_data(
        sensor_name, start_date, end_date, http_client
    )
    predicted_data_task = pred_client.get_predicted_data(
        sensor_name, start_date, end_date, http_client
    )

    results = await asyncio.gather(
        real_data_task,
        predicted_data_task,
        return_exceptions=True # Allow us to handle individual errors
    )

    real_data_response = results[0]
    predicted_data_response = results[1]

    # Error handling for DigitalTwinAPI
    if isinstance(real_data_response, DigitalTwinAPIConnectionError):
        raise HTTPException(status_code=503, detail=f"DigitalTwinAPI connection error: {real_data_response.message}")
    if isinstance(real_data_response, DigitalTwinAPIHttpError):
        status = 502 if real_data_response.status_code != 404 else 404
        raise HTTPException(status_code=status, detail=f"DigitalTwinAPI error: {real_data_response.message}")
    if isinstance(real_data_response, DigitalTwinAPIDataValidationError):
        raise HTTPException(status_code=502, detail=f"DigitalTwinAPI data validation error: {real_data_response.message}")
    if isinstance(real_data_response, DigitalTwinAPIError): # Other specific client errors
        raise HTTPException(status_code=500, detail=f"DigitalTwinAPI internal error: {real_data_response.message}")
    if isinstance(real_data_response, Exception): # Unexpected error from this task
        # Log this error properly in a real application
        print(f"Unexpected error fetching real data: {real_data_response}")
        raise HTTPException(status_code=500, detail="Internal server error fetching real data.")


    # Error handling for PredictionModelAPI
    # We might choose to return partial data if one service fails,
    # but for now, let's assume both are needed or raise an error.
    # If predictions are optional, you might just log the error and proceed.
    real_data_points = real_data_response.data if real_data_response else []
    predicted_data_points = []

    if isinstance(predicted_data_response, PredictionAPIConnectionError):
        # Option: Log and proceed with only real data, or raise error
        # For now, let's make predictions optional and proceed with a warning in message
        # Or, if predictions are critical, raise HTTPException like above.
        # Here, I'll assume we can proceed but the data will lack predictions.
        # A more sophisticated approach might involve a flag in the response.
        print(f"Warning: PredictionModelAPI connection error: {predicted_data_response.message}")
    elif isinstance(predicted_data_response, PredictionAPIHttpError):
        print(f"Warning: PredictionModelAPI HTTP error: {predicted_data_response.message}")
    elif isinstance(predicted_data_response, PredictionAPIDataValidationError):
        print(f"Warning: PredictionModelAPI data validation error: {predicted_data_response.message}")
    elif isinstance(predicted_data_response, PredictionAPIError):
        print(f"Warning: PredictionModelAPI internal error: {predicted_data_response.message}")
    elif isinstance(predicted_data_response, Exception):
        print(f"Warning: Unexpected error fetching predicted data: {predicted_data_response}")
    elif predicted_data_response: # Success
        predicted_data_points = predicted_data_response.data


    # If real_data_response itself was an exception not caught by specific handlers above
    if not real_data_points and isinstance(real_data_response, Exception):
         raise HTTPException(status_code=500, detail="Failed to retrieve essential real data.")


    # Merge data
    # If real_data_response is None or an error, real_data_points will be empty.
    # If predicted_data_response is an error, predicted_data_points will be empty.
    
    # If real_data_response was an error and we raised, this part isn't reached.
    # If only predicted_data_response had an error, real_data_points is populated,
    # predicted_data_points is empty. The merge function should handle this.

    if not real_data_response and not predicted_data_response: # Both failed critically earlier
        raise HTTPException(status_code=500, detail="Failed to retrieve data from any source.")
    
    # Ensure real_data_points is from a successful call
    # The earlier checks for real_data_response should have raised if it was an error.
    # So, if we are here, real_data_response should be a valid SensorDataResponse object.
    
    final_response = merge_sensor_data(
        sensor_name,
        real_data_points, # from real_data_response.data
        predicted_data_points # from predicted_data_response.data (or empty list)
    )

    # Modify message if predictions are missing due to an error
    if isinstance(predicted_data_response, Exception) and final_response.message:
        final_response.message = (
            f"{final_response.message}. Predictions might be incomplete due to an error: "
            f"{str(predicted_data_response)}"
        )
    elif not predicted_data_points and not isinstance(predicted_data_response, Exception) and predicted_data_response is not None:
        # Prediction API call was successful but returned no data points
        if final_response.message:
             final_response.message += ". No predicted data points were available for this period."


    return final_response
