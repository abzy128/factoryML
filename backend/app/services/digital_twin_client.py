import httpx
from datetime import datetime, timezone
from typing import Optional
from pydantic import ValidationError

from app.core.config import settings
from app.api.v1.schemas.timeseries_schemas import SensorDataResponse

# Custom Exceptions for the client
class DigitalTwinAPIError(Exception):
    """Base exception for DigitalTwinAPI client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class DigitalTwinAPIConnectionError(DigitalTwinAPIError):
    """Raised for network issues connecting to the API."""
    def __init__(self, original_exception: httpx.RequestError):
        super().__init__(
            f"Connection error to DigitalTwinAPI: {original_exception}"
        )

class DigitalTwinAPIHttpError(DigitalTwinAPIError):
    """Raised for HTTP errors from the API (4xx, 5xx)."""
    def __init__(self, response: httpx.Response):
        detail = f"DigitalTwinAPI request failed: {response.status_code}"
        try:
            # Try to include response text for more context
            error_text = response.text
            if error_text:
                detail += f" - {error_text[:200]}" # Limit length
        except Exception:
            pass # Ignore if response text is not available or causes error
        super().__init__(detail, status_code=response.status_code)
        self.response_text = response.text


class DigitalTwinAPIDataValidationError(DigitalTwinAPIError):
    """Raised when API response data doesn't match the expected schema."""
    def __init__(self, validation_error: ValidationError):
        super().__init__(
            f"Data validation error from DigitalTwinAPI response: {validation_error}"
        )

class DigitalTwinAPIClient:
    def __init__(
        self,
        base_url: str = settings.DIGITAL_TWIN_API_BASE_URL,
        endpoint: str = settings.DIGITAL_TWIN_API_ENDPOINT,
    ):
        self.base_url = base_url
        self.endpoint = endpoint

    def _format_datetime_for_api(self, dt: datetime) -> str:
        """Ensures datetime is UTC and formats to ISO 8601 with 'Z'."""
        if dt.tzinfo is None:
            dt_utc = dt.replace(tzinfo=timezone.utc)
        else:
            dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def get_sensor_data(
        self,
        sensor_name: str,
        start_date: datetime,
        end_date: datetime,
        http_client: httpx.AsyncClient, # Pass managed httpx client
    ) -> SensorDataResponse:
        params = {
            "sensorName": sensor_name,
            "startDate": self._format_datetime_for_api(start_date),
            "endDate": self._format_datetime_for_api(end_date),
        }
        url = f"{self.base_url}{self.endpoint}"

        try:
            response = await http_client.get(url, params=params, timeout=10.0)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx
            
            response_json = response.json()
            return SensorDataResponse(**response_json)
        
        except httpx.HTTPStatusError as e:
            raise DigitalTwinAPIHttpError(response=e.response) from e
        except httpx.RequestError as e:
            raise DigitalTwinAPIConnectionError(original_exception=e) from e
        except ValidationError as e:
            raise DigitalTwinAPIDataValidationError(validation_error=e) from e
        except Exception as e: # Catch any other unexpected errors
            raise DigitalTwinAPIError(
                f"An unexpected error occurred while fetching data: {str(e)}"
            ) from e

# Factory function for dependency injection
def get_digital_twin_api_client():
    return DigitalTwinAPIClient()
