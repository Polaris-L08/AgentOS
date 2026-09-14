from __future__ import annotations

from sqlalchemy import text

from runtime.persistence.models import PersistenceBase
from runtime.persistence.postgres import PostgresDatabase


class PostgresSchemaManager:
    """
    Creates the database schema for AgentOS persistence models.

    This is a development/bootstrap utility.

    It is intentionally not a migration system.
    """

    def __init__(
        self,
        database: PostgresDatabase,
    ) -> None:
        self._database = database

    async def check_connection(self) -> None:
        """
        验证数据库可连接
        """
        async with self._database.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def create_all(self) -> None:
        """
        创建 Persistence Model 对应的表
        """
        async with self._database.engine.begin() as connection:
            await connection.run_sync(
                PersistenceBase.metadata.create_all
            )