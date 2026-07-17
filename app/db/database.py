from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Set this in your .env file. You can set it to whatever user and password you want. For example:
# DATABASE_URL=postgresql+asyncpg://pdfagent_user:yourpassword@localhost:5432/pdfagent
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://pdfagent_user:yourpassword@localhost:5432/pdfagent")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a DB session, closes it after the request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
