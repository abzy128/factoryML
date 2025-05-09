import httpx
from datetime import datetime, timedelta, timezone
import random
from app.core.config import settings
from app.api.v1 import schemas # For DataPointCreate
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

# This is a MOCK service. In a real scenario, it would call the actual ML model service.
async def fetch_predicted_data_from_ml_model(
    start_time: datetime, end_time: datetime
) -> List[schemas.DataPointCreate]:
    """
    Mocks fetching predicted data from an ML model service.
    Generates data every 15 minutes for the requested period.
    """
    data_points = []
    current_time = start_time
    # Ensure timezones are consistent (UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    logger.info(f"Mock ML Service: Fetching predictions from {start_time} to {end_time}")

    # Simulate calling an external API
    # async with httpx.AsyncClient() as client:
    #     try:
    #         response = await client.get(
    #             f"{settings.ML_HOST}/predict",
    #             params={"startTime": start_time.isoformat(), "endTime": end_time.isoformat()}
    #         )
    #         response.raise_for_status()
    #         # raw_data = response.json()
    #         # for item in raw_data:
    #         #    data_points.append(schemas.DataPointCreate(timestamp=item['timestamp'], value=item['value']))
    #         # return data_points
    #     except httpx.HTTPStatusError as e:
    #         logger.error(f"ML service HTTP error: {e.response.status_code} - {e.response.text}")
    #         return []
    #     except httpx.RequestError as e:
    #         logger.error(f"ML service request error: {e}")
    #         return []

    # Mocked data generation:
    while current_time <= end_time:
        aware_timestamp = current_time.astimezone(timezone.utc)
        data_points.append(
            schemas.DataPointCreate(
                timestamp=aware_timestamp,
                value=random.uniform(22.0, 28.0) + random.uniform(-2.0, 2.0) # Example predicted value
            )
        )
        current_time += timedelta(minutes=15) # Predictions every 15 minutes

    logger.info(f"Mock ML Service: Generated {len(data_points)} data points.")
    return data_points

