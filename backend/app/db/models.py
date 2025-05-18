from sqlalchemy import Column, String, DateTime, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.db.session import Base
from app.core.config import settings


class SensorDataTS(Base):
    __tablename__ = settings.TIMESERIES_TABLE_NAME

    sensor_name = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True, index=True)
    real_value = Column(Float, nullable=True)
    predicted_value = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint('sensor_name', 'timestamp', name='uq_sensor_timestamp'),
    )

    @classmethod
    async def bulk_upsert(cls, session: AsyncSession, data_points: List[Dict[str, Any]]):
        if not data_points:
            return

        stmt = pg_insert(cls).values(data_points)
        
        # For COALESCE to work correctly, ensure that keys not present in a dict 
        # are not passed to the INSERT statement, or handle them appropriately.
        # The default behavior of pg_insert should handle missing keys by using defaults or NULL.
        
        # Update existing rows, preserving values not being updated
        # If EXCLUDED.real_value is NULL (not part of this upsert batch for this row), keep existing value.
        # If EXCLUDED.real_value is provided, use it.
        update_dict = {
            "real_value": stmt.excluded.real_value,
            "predicted_value": stmt.excluded.predicted_value,
        }
        
        # More robust COALESCE logic if a value might be explicitly set to None in data_points
        # vs. not being present at all. For simplicity, assuming None means "no update for this field".
        # A more explicit way:
        # update_dict = {
        #     # Only update if EXCLUDED has a non-null value for the field,
        #     # otherwise keep the existing value.
        #     # This requires careful handling of how data_points are constructed.
        #     # A simpler approach is to always set both, and if one is not provided
        #     # in the source data, it should be None in data_points.
        #     "real_value": case(
        #         (stmt.excluded.real_value != None, stmt.excluded.real_value),
        #         else_=cls.real_value
        #     ),
        #     "predicted_value": case(
        #         (stmt.excluded.predicted_value != None, stmt.excluded.predicted_value),
        #         else_=cls.predicted_value
        #     ),
        # }


        # This COALESCE strategy ensures that if an incoming point only has 'real_value',
        # an existing 'predicted_value' for that (sensor_name, timestamp) is not wiped out.
        stmt = stmt.on_conflict_do_update(
            index_elements=['sensor_name', 'timestamp'],
            set_={
                'real_value': stmt.excluded.real_value, # If EXCLUDED.real_value is NULL, this will set it to NULL
                'predicted_value': stmt.excluded.predicted_value # If EXCLUDED.predicted_value is NULL, this will set it to NULL
            }
        )
        # To preserve existing values if the new value is NULL (meaning not provided in this batch):
        # stmt = stmt.on_conflict_do_update(
        #     index_elements=['sensor_name', 'timestamp'],
        #     set_={
        #         'real_value': func.coalesce(stmt.excluded.real_value, cls.real_value),
        #         'predicted_value': func.coalesce(stmt.excluded.predicted_value, cls.predicted_value)
        #     }
        # )
        # The above COALESCE is generally better. Requires `from sqlalchemy import func, case`.
        # For now, the simpler direct assignment is used. If a value is not in the `data_points` dict
        # for a particular point, it will be inserted as NULL. If it IS in the dict and is None, it will be NULL.
        # This means if you fetch real data, predicted_value will be NULL in the upsert list for those points.
        # If you then fetch predicted data, real_value will be NULL in the upsert list for those points.
        # The `on_conflict_do_update` will then update the respective columns.

        await session.execute(stmt)
        await session.commit()

