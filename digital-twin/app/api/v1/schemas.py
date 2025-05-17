from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Union

class DataPoint(BaseModel):
    timestamp: datetime
    value: Union[float, int, str] # Allow various types for sensor values

class SensorDataRequest(BaseModel):
    sensorName: str = Field(..., example="ActivePower")
    startDate: datetime = Field(..., example="2025-01-25T08:00:00Z")
    endDate: datetime = Field(..., example="2025-01-25T09:00:00Z")

class SensorDataResponse(BaseModel):
    sensorName: str
    data: List[DataPoint]
    message: str = "Data fetched successfully"