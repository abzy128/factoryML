from fastapi import APIRouter, HTTPException, Query, Depends, Path
from datetime import datetime
import httpx

from app.api.v1.schemas.timeseries_schemas import SensorDataResponse
from app.services.digital_twin_client import (
    DigitalTwinAPIClient,
    DigitalTwinAPIConnectionError,
    DigitalTwinAPIHttpError,
    DigitalTwinAPIDataValidationError,
    DigitalTwinAPIError,
    get_digital_twin_api_client, # Factory for the service client
)

router = APIRouter()

# Dependency for httpx.AsyncClient, managed per request
async def get_http_client():
    async with httpx.AsyncClient() as client:
        yield client

@router.get(
    "/{sensor_name}",
    response_model=SensorDataResponse,
    summary="Get time-series data for a specific sensor",
)
async def get_sensor_data_endpoint(
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
    service_client: DigitalTwinAPIClient = Depends(get_digital_twin_api_client),
    http_client: httpx.AsyncClient = Depends(get_http_client),
):
    """
    Retrieves time-series data for a specified sensor within a given date range
    by fetching it from an external Digital Twin API.
    """
    if start_date >= end_date:
        raise HTTPException(
            status_code=400, detail="endDate must be after startDate"
        )

    try:
        response_data = await service_client.get_sensor_data(
            sensor_name=sensor_name,
            start_date=start_date,
            end_date=end_date,
            http_client=http_client,
        )
        return response_data
    except DigitalTwinAPIConnectionError as e:
        raise HTTPException(
            status_code=503, # Service Unavailable
            detail=f"Could not connect to the DigitalTwinAPI: {e.message}",
        )
    except DigitalTwinAPIHttpError as e:
        # Map external API errors to appropriate gateway errors
        if e.status_code == 404:
            raise HTTPException(
                status_code=404, # Not Found
                detail=f"Sensor '{sensor_name}' not found by the external service or no data available. Upstream: {e.message}",
            )
        # For other client errors (4xx) or server errors (5xx) from upstream
        # return 502 Bad Gateway
        raise HTTPException(
            status_code=502, # Bad Gateway
            detail=f"Error from DigitalTwinAPI: {e.message}",
        )
    except DigitalTwinAPIDataValidationError as e:
        raise HTTPException(
            status_code=502, # Bad Gateway
            detail=f"Invalid data format from DigitalTwinAPI: {e.message}",
        )
    except DigitalTwinAPIError as e: # Catch-all for other specific client errors
        raise HTTPException(
            status_code=500, # Internal Server Error
            detail=f"An error occurred while processing your request: {e.message}",
        )
    except Exception as e: # Fallback for truly unexpected errors
        # Log this error, as it's not a handled client exception
        print(f"Unexpected internal server error: {e}") # Basic logging
        raise HTTPException(
            status_code=500, detail="An unexpected internal server error occurred."
        )
