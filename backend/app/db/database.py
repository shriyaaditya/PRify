from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

# Create the async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    future=True,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=20,
    max_overflow=10,
)
