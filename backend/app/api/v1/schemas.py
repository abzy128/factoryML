from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class DataPointBase(BaseModel):
    timestamp: datetime
    value: float

class DataPointCreate(DataPointBase):
    pass

class DataPoint(DataPointBase):
    source: Optional[str] = None # Will be set by the endpoint logic

    class Config:
        orm_mode = True # For SQLAlchemy model compatibility (though we use dicts here)
        # Pydantic V2 uses `from_attributes = True` instead of `orm_mode = True`
        # from_attributes = True


class DataQuery(BaseModel):
    startTime: datetime = Field(..., example="2025-05-09T10:00:00Z")
    endTime: datetime = Field(..., example="2025-05-09T12:00:00Z")

class DataResponse(BaseModel):
    data: List[DataPoint]
    message: Optional[str] = None

