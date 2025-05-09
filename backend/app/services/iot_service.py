import httpx
from datetime import datetime, timedelta, timezone
import random
from app.core.config import settings
from app.api.v1 import schemas # For DataPointCreate
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

# This is a MOCK service. In a real scenario, it would call the actual IoT digital twin.
async def fetch_real_data_from_iot_twin(
    start_time: datetime, end_time: datetime
) -> List[schemas.DataPointCreate]:
    """
    Mocks fetching real data from an IoT digital twin service.
    Generates data every 5 minutes for the requested period.
    """
    data_points = []
    current_time = start_time
    # Ensure timezones are consistent (UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    logger.info(f"Mock IoT Service: Fetching data from {start_time} to {end_time}")

    # Simulate calling an external API
    # async with httpx.AsyncClient() as client:
    #     try:
    #         response = await client.get(
    #             f"{settings.IOT_HOST}/data",
    #             params={"startTime": start_time.isoformat(), "endTime": end_time.isoformat()}
    #         )
    #         response.raise_for_status()
    #         # Assuming the external service returns data in a compatible format
    #         # raw_data = response.json()
    #         # for item in raw_data:
    #         #    data_points.append(schemas.DataPointCreate(timestamp=item['timestamp'], value=item['value']))
    #         # return data_points
    #     except httpx.HTTPStatusError as e:
    #         logger.error(f"IoT service HTTP error: {e.response.status_code} - {e.response.text}")
    #         return []
    #     except httpx.RequestError as e:
    #         logger.error(f"IoT service request error: {e}")
    #         return []

    # Mocked data generation:
    while current_time <= end_time:
        # Ensure generated timestamps are timezone-aware (UTC)
        aware_timestamp = current_time.astimezone(timezone.utc)
        data_points.append(
            schemas.DataPointCreate(
                timestamp=aware_timestamp,
                value=random.uniform(20.0, 30.0) # Example real value
            )
        )
        current_time += timedelta(minutes=5) # Data every 5 minutes

    logger.info(f"Mock IoT Service: Generated {len(data_points)} data points.")
    return data_points

