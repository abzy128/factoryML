import httpx
from datetime import datetime, timezone
from typing import Optional
from pydantic import ValidationError

from app.core.config import settings
from app.api.v1.schemas.timeseries_schemas import PredictionDataResponse # Use the new schema

# Re-using or adapting exception classes from digital_twin_client
# For brevity, let's assume similar error classes or a shared error module
# For this example, I'll define them here, but in a larger app, refactor to common_exceptions.py
class PredictionAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class PredictionAPIConnectionError(PredictionAPIError):
    def __init__(self, original_exception: httpx.RequestError):
        super().__init__(
            f"Connection error to PredictionModelAPI: {original_exception}"
        )

class PredictionAPIHttpError(PredictionAPIError):
    def __init__(self, response: httpx.Response):
        detail = f"PredictionModelAPI request failed: {response.status_code}"
        try:
            error_text = response.text
            if error_text:
                detail += f" - {error_text[:200]}"
        except Exception:
            pass
        super().__init__(detail, status_code=response.status_code)
        self.response_text = response.text


class PredictionAPIDataValidationError(PredictionAPIError):
    def __init__(self, validation_error: ValidationError):
        super().__init__(
            f"Data validation error from PredictionModelAPI response: {validation_error}"
        )


class PredictionModelAPIClient:
    def __init__(
        self,
        base_url: str = settings.PREDICTION_MODEL_API_BASE_URL,
        endpoint: str = settings.PREDICTION_MODEL_API_ENDPOINT,
    ):
        self.base_url = base_url
        self.endpoint = endpoint

    def _format_datetime_for_api(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt_utc = dt.replace(tzinfo=timezone.utc)
        else:
            dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def get_predicted_data(
        self,
        sensor_name: str,
        start_date: datetime,
        end_date: datetime,
        http_client: httpx.AsyncClient,
    ) -> PredictionDataResponse:
        # Assuming prediction API uses similar query parameters
        params = {
            "sensorName": sensor_name,
            "startDate": self._format_datetime_for_api(start_date),
            "endDate": self._format_datetime_for_api(end_date),
        }
        url = f"{self.base_url}{self.endpoint}"

        try:
            response = await http_client.get(url, params=params, timeout=900.0)
            response.raise_for_status()
            
            response_json = response.json()
            # Ensure the response matches PredictionDataResponse
            # The external API might return a slightly different structure,
            # adapt PredictionDataResponse or parsing here if needed.
            return PredictionDataResponse(**response_json)
        
        except httpx.HTTPStatusError as e:
            raise PredictionAPIHttpError(response=e.response) from e
        except httpx.RequestError as e:
            raise PredictionAPIConnectionError(original_exception=e) from e
        except ValidationError as e:
            raise PredictionAPIDataValidationError(validation_error=e) from e
        except Exception as e:
            raise PredictionAPIError(
                f"An unexpected error occurred while fetching predicted data: {str(e)}"
            ) from e

def get_prediction_model_api_client():
    return PredictionModelAPIClient()
