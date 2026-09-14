from __future__ import annotations

from collections.abc import AsyncIterator

from click import echo
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from runtime.persistence.database_config import DatabaseConfig


class PostgresDatabase:
    """
    PostgreSQL database access component.

    This component owns the SQLAlchemy async engine and session factory.
    It does not know anything about AgentOS runtime objects.
    """

    def __init__(
        self,
        config: DatabaseConfig,
    ) -> None:
        self._config = config

        self._engine: AsyncEngine = create_async_engine(
            config.database_url,
            echo=config.echo,
            pool_pre_ping=config.pool_pre_ping,
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