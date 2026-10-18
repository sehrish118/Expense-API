from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    url=settings.database_url, pool_size=5, max_overflow=10, pool_pre_ping=True
)


async_session = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)  # this is session making factory


# dependency injection provider for API routes
async def get_db() -> AsyncGenerator[
    AsyncSession, None
]:  # asyncgenerator tells that this function will generate async session one by one
    async with (
        async_session() as session
    ):  # async with is context manager.This tells when this block start, give session to db and when it ends , close that session automatically
        try:
            yield session

        finally:  # this always run
            await session.close()
