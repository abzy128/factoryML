from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Union, Any

class DataPoint(BaseModel):
    timestamp: datetime
    value: Union[float, int, str] # Allow various types for sensor values

class SensorDataRequest(BaseModel):
    sensorName: str = Field(..., example="furnace_1_temperature")
    startDate: datetime = Field(..., example="2025-05-10T08:00:00Z")
    endDate: datetime = Field(..., example="2025-05-10T18:00:00Z")

class SensorDataResponse(BaseModel):
    sensorName: str
    data: List[DataPoint]
    message: str = "Data generated successfully"

