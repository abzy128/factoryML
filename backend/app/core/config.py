import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Time-Series Gateway"
    APP_VERSION: str = "0.1.0"
    
    # External DigitalTwinAPI settings
    DIGITAL_TWIN_API_BASE_URL: str = "http://127.0.0.1:8002"
    DIGITAL_TWIN_API_ENDPOINT: str = "/api/v1/sensor/data/api/v1/sensor/data"

    # External PredictionModelAPI settings
    PREDICTION_MODEL_API_BASE_URL: str = "http://127.0.0.1:8003"
    PREDICTION_MODEL_API_ENDPOINT: str = "/api/v1/sensor/predict"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/postgres"
    )
    
    TIMESERIES_TABLE_NAME: str = "sensor_data_ts"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
