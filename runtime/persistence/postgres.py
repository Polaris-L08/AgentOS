from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class PostgresDatabase:
    """
    PostgreSQL database access component.

    This component owns the SQLAlchemy async engine and session factory.
    It does not know anything about AgentOS runtime objects.
    """

    def __init__(
        self,
        database_url: str,
    ) -> None:
        self._engine: AsyncEngine = create_async_engine(
            database_url,
            future=True,
        )

        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    def session(self) -> AsyncSession:
        return self._session_factory()

    async def close(self) -> None:
        await self._engine.dispose()

    async def sessions(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session