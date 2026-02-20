from sqlalchemy import select

from app.database.models import (
    HW_TYPES,
    Base,
    HomeworkSettings,
    async_session,
    engine,
)

__all__ = [
    "Base",
    "async_session",
    "engine",
    "async_main",
]


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _ensure_homework_settings()


async def _ensure_homework_settings():
    """Create HomeworkSettings rows for each hw type if they don't exist yet."""
    async with async_session() as session:
        for hw_type in HW_TYPES:
            exists = await session.scalar(
                select(HomeworkSettings).where(HomeworkSettings.hw_type == hw_type)
            )
            if not exists:
                session.add(HomeworkSettings(hw_type=hw_type, available=False))
        await session.commit()
