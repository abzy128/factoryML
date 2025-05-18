from datetime import datetime
from typing import List, Union, Optional
from pydantic import BaseModel, Field

class DataPoint(BaseModel):
    timestamp: datetime
    value: Union[float, int, str, None]

class SensorDataResponse(BaseModel):
    sensorName: str
    data: List[DataPoint]
    message: Optional[str] = "Data fetched successfully"

class SensorDataRequest(BaseModel):
    sensorName: str = Field(..., example="ActivePower")
    startDate: datetime = Field(..., example="2025-01-25T08:00:00Z")
    endDate: datetime = Field(..., example="2025-01-25T09:00:00Z")

class PredictionDataResponse(BaseModel):
    sensorName: str # Or whatever identifier the prediction API uses
    data: List[DataPoint] # List of DataPoint with predicted values
    message: Optional[str] = "Predicted data fetched successfully"

# Schemas for the combined output
class CombinedDataPoint(BaseModel):
    timestamp: datetime
    predicted_value: Optional[Union[float, int, str, None]] = None
    real_value: Optional[Union[float, int, str, None]] = None

class CombinedSensorDataResponse(BaseModel):
    sensorName: str
    data: List[CombinedDataPoint]
    message: str = "Data fetched successfully"