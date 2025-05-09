from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Define the table name
SENSOR_DATA_TABLE_NAME = "sensor_data"

# Create an async engine instance
engine = create_async_engine(settings.DATABASE_URL, echo=False) # Set echo=True for SQL logging

# Create a configured "AsyncSession" class
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """
    Initializes the database, creates the table and hypertable if they don't exist.
    """
    async with engine.connect() as conn:
        try:
            # Check if TimescaleDB extension is enabled
            result = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'"))
            if not result.scalar_one_or_none():
                logger.warning("TimescaleDB extension not found. Attempting to create.")
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                logger.info("TimescaleDB extension created (or already existed).")

            # Create the sensor_data table
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {SENSOR_DATA_TABLE_NAME} (
                    timestamp TIMESTAMPTZ NOT NULL,
                    value DOUBLE PRECISION,
                    source TEXT NOT NULL,
                    PRIMARY KEY (timestamp, source) -- Ensures uniqueness for ON CONFLICT
                );
            """))
            logger.info(f"Table '{SENSOR_DATA_TABLE_NAME}' created or already exists.")

            # Create the hypertable
            # Check if it's already a hypertable to avoid errors
            hypertable_check = await conn.execute(text(f"""
                SELECT 1 FROM timescaledb_information.hypertables
                WHERE hypertable_name = '{SENSOR_DATA_TABLE_NAME}';
            """))
            if not hypertable_check.scalar_one_or_none():
                await conn.execute(text(
                    f"SELECT create_hypertable('{SENSOR_DATA_TABLE_NAME}', 'timestamp', if_not_exists => TRUE);"
                ))
                logger.info(f"Hypertable for '{SENSOR_DATA_TABLE_NAME}' created or already exists.")
            else:
                logger.info(f"'{SENSOR_DATA_TABLE_NAME}' is already a hypertable.")

            # Create an index for efficient querying
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_sensor_data_source_timestamp
                ON {SENSOR_DATA_TABLE_NAME} (source, timestamp DESC);
            """))
            logger.info("Index 'idx_sensor_data_source_timestamp' created or already exists.")

            await conn.commit()
            logger.info("Database initialization complete.")
        except Exception as e:
            await conn.rollback()
            logger.error(f"Error during database initialization: {e}")
            raise

async def get_db() -> AsyncSession:
    """
    Dependency to get an async database session.
    """
    async with AsyncSessionLocal() as session:
        yield session

