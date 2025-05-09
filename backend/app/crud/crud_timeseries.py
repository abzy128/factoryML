from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.api.v1 import schemas
from app.db.session import SENSOR_DATA_TABLE_NAME
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def get_data_by_source_and_time_range(
    db: AsyncSession, *, source: str, start_time: datetime, end_time: datetime
) -> List[Dict[str, Any]]:
    """
    Retrieves data points for a given source within a time range.
    """
    query = text(f"""
        SELECT timestamp, value, source
        FROM {SENSOR_DATA_TABLE_NAME}
        WHERE source = :source AND timestamp >= :start_time AND timestamp <= :end_time
        ORDER BY timestamp ASC;
    """)
    result = await db.execute(query, {"source": source, "start_time": start_time, "end_time": end_time})
    rows = result.mappings().all() # Returns list of dict-like RowMapping objects
    return [dict(row) for row in rows]


async def bulk_insert_data_points(
    db: AsyncSession, *, data_points: List[schemas.DataPointCreate], source: str
):
    """
    Bulk inserts data points for a given source.
    Uses ON CONFLICT DO NOTHING to avoid duplicates based on (timestamp, source) PK.
    """
    if not data_points:
        return 0

    values_to_insert = [
        {"timestamp": dp.timestamp, "value": dp.value, "source": source}
        for dp in data_points
    ]

    # Using SQLAlchemy Core for ON CONFLICT with asyncpg
    # This requires defining the table metadata or using text-based for simplicity here
    # For more complex scenarios, SQLAlchemy Table object is preferred.

    # Constructing the insert statement with ON CONFLICT
    # Note: This is a simplified way. For full SQLAlchemy ORM/Core benefits,
    # you'd define the table metadata.
    insert_stmt = f"""
        INSERT INTO {SENSOR_DATA_TABLE_NAME} (timestamp, value, source)
        VALUES (:timestamp, :value, :source)
        ON CONFLICT (timestamp, source) DO NOTHING;
    """
    try:
        # Execute in a transaction
        async with db.begin(): # Ensures commit or rollback
            result = await db.execute(text(insert_stmt), values_to_insert)
        # The 'result.rowcount' for INSERT ... ON CONFLICT DO NOTHING in PostgreSQL
        # typically reports the number of rows inserted, not rows processed.
        # If you need to know how many were attempted vs inserted, it's more complex.
        logger.info(f"Bulk insert for source '{source}': {result.rowcount} new rows inserted.")
        return result.rowcount
    except Exception as e:
        logger.error(f"Error during bulk insert for source '{source}': {e}")
        await db.rollback() # Ensure rollback if begin() wasn't used or failed mid-way
        raise

