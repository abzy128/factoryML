from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.core.config import settings

async_engine = create_async_engine(settings.DATABASE_URL, echo=False) # Set echo=True for SQL logging

AsyncSessionFactory = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_async_db() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    async with async_engine.connect() as conn:
        # Create extension if not exists (requires superuser or specific grants)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
        await conn.commit() # Commit extension creation

    async with async_engine.begin() as conn:
        # Create all tables defined by Base's subclasses
        await conn.run_sync(Base.metadata.create_all)
    
    # Create hypertable after the table is created by SQLAlchemy
    async with AsyncSessionFactory() as session:
        try:
            # Check if it's already a hypertable
            # This check is a bit simplified; a more robust check might query TimescaleDB's metadata
            check_hyper_sql = text(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM timescaledb_information.hypertables
                    WHERE hypertable_name = '{settings.TIMESERIES_TABLE_NAME}'
                );
            """)
            result = await session.execute(check_hyper_sql)
            is_hypertable = result.scalar_one_or_none()

            if not is_hypertable:
                create_hyper_sql = text(
                    f"SELECT create_hypertable("
                    f"'{settings.TIMESERIES_TABLE_NAME}', "
                    f"'timestamp', "
                    f"if_not_exists => TRUE, "
                    f"chunk_time_interval => INTERVAL '7 days'" # Adjust as needed
                    f");"
                )
                await session.execute(create_hyper_sql)
                await session.commit()
                print(f"Hypertable '{settings.TIMESERIES_TABLE_NAME}' created or already exists.")
            else:
                print(f"Hypertable '{settings.TIMESERIES_TABLE_NAME}' already exists.")

        except SQLAlchemyError as e:
            await session.rollback()
            print(f"Error during hypertable creation for {settings.TIMESERIES_TABLE_NAME}: {e}")
        except Exception as e: # Catch other potential errors like connection issues
            print(f"An unexpected error occurred during init_db: {e}")

