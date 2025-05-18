from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert # Ensure this is imported
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime, timezone

from app.db.models import SensorDataTS
from app.api.v1.schemas.timeseries_schemas import CombinedDataPoint, DataPoint as SourceDataPoint

def truncate_to_minute(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(second=0, microsecond=0)

async def get_sensor_data_from_db(
    db: AsyncSession,
    sensor_name: str,
    start_date: datetime,
    end_date: datetime,
) -> List[CombinedDataPoint]:
    
    start_date_trunc = truncate_to_minute(start_date)
    end_date_trunc = truncate_to_minute(end_date)

    stmt = (
        select(SensorDataTS)
        .where(
            SensorDataTS.sensor_name == sensor_name,
            SensorDataTS.timestamp >= start_date_trunc,
            SensorDataTS.timestamp <= end_date_trunc,
        )
        .order_by(SensorDataTS.timestamp)
    )
    result = await db.execute(stmt)
    db_records = result.scalars().all()
    
    return [
        CombinedDataPoint(
            timestamp=record.timestamp,
            real_value=record.real_value,
            predicted_value=record.predicted_value,
        )
        for record in db_records
    ]

async def upsert_sensor_data_points_db(
    db: AsyncSession,
    sensor_name: str,
    api_data_points: List[SourceDataPoint], 
    value_type: str, # "real" or "predicted"
):
    if not api_data_points:
        return

    points_to_upsert = []
    for dp in api_data_points:
        point_data = {
            "sensor_name": sensor_name,
            "timestamp": truncate_to_minute(dp.timestamp),
        }
        if value_type == "real":
            point_data["real_value"] = dp.value
            # For COALESCE to work as intended, don't set predicted_value if it's not from this source
        elif value_type == "predicted":
            point_data["predicted_value"] = dp.value
            # Don't set real_value
        points_to_upsert.append(point_data)

    if not points_to_upsert:
        return

    stmt = pg_insert(SensorDataTS).values(points_to_upsert)
    
    # This logic ensures that we only update the field we have new data for.
    # If inserting real data, predicted_value in DB should remain untouched if it exists.
    # If inserting predicted data, real_value in DB should remain untouched.
    update_values = {}
    if value_type == "real":
        update_values[SensorDataTS.real_value.name] = stmt.excluded.real_value
        # To preserve existing predicted_value if not explicitly overwritten by a future predicted data upsert:
        #update_values[SensorDataTS.predicted_value.name] = func.coalesce(stmt.excluded.predicted_value, SensorDataTS.predicted_value)

    elif value_type == "predicted":
        update_values[SensorDataTS.predicted_value.name] = stmt.excluded.predicted_value
        # To preserve existing real_value:
        #update_values[SensorDataTS.real_value.name] = func.coalesce(stmt.excluded.real_value, SensorDataTS.real_value)


    # A more general upsert that updates provided fields and preserves others:
    # This assumes `points_to_upsert` contains dicts where keys not present mean "do not update this field".
    # However, standard SQL INSERT will treat missing fields as NULL.
    # The COALESCE strategy is generally better for partial updates.

    # Corrected on_conflict_do_update:
    # If inserting real data, update real_value, keep existing predicted_value.
    # If inserting predicted data, update predicted_value, keep existing real_value.
    
    set_clause = {}
    if value_type == "real":
        set_clause['real_value'] = stmt.excluded.real_value
        # If predicted_value was also part of EXCLUDED (i.e., points_to_upsert had it),
        # and it was NULL, this would nullify existing. So, be careful.
        # The COALESCE approach is safer if points_to_upsert only contains the relevant value type.
        #set_clause['predicted_value'] = func.coalesce(SensorDataTS.predicted_value, stmt.excluded.predicted_value) # Keep existing if new is null
        func.coalesce(SensorDataTS.predicted_value, stmt.excluded.predicted_value) # Keep existing if new is null
    elif value_type == "predicted":
        set_clause['predicted_value'] = stmt.excluded.predicted_value
        #set_clause['real_value'] = func.coalesce(SensorDataTS.real_value, stmt.excluded.real_value)
        func.coalesce(SensorDataTS.real_value, stmt.excluded.real_value)


    # Final refined upsert logic for clarity and correctness:
    # When upserting "real" values, we only want to affect real_value.
    # When upserting "predicted" values, we only want to affect predicted_value.
    final_set_clause = {}
    if value_type == "real":
        final_set_clause[SensorDataTS.real_value.name] = stmt.excluded.real_value
    elif value_type == "predicted":
        final_set_clause[SensorDataTS.predicted_value.name] = stmt.excluded.predicted_value
    
    # This ensures that only the specified value_type column is updated from EXCLUDED,
    # other columns are not touched by the UPDATE part of ON CONFLICT.
    # If the row doesn't exist, it's inserted with one value and NULL for the other.
    # If it exists, only the specified value is updated.

    stmt = stmt.on_conflict_do_update(
        index_elements=[SensorDataTS.sensor_name, SensorDataTS.timestamp],
        set_=final_set_clause
    )

    await db.execute(stmt)
