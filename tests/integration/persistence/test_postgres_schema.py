from __future__ import annotations

import os

import pytest

from runtime.persistence import (
    DatabaseConfig,
    PostgresDatabase,
    PostgresSchemaManager,
)


POSTGRES_DATABASE_URL = os.getenv(
    "AGENTOS_TEST_DATABASE_URL",
    "postgresql+asyncpg://agentos:agentos@192.168.0.170:5432/agentos",
)


@pytest.mark.asyncio
async def test_postgres_connection() -> None:
    database = PostgresDatabase(
        DatabaseConfig(
            database_url=POSTGRES_DATABASE_URL,
        )
    )

    try:
        schema_manager = PostgresSchemaManager(database)

        await schema_manager.check_connection()
    finally:
        await database.close()


@pytest.mark.asyncio
async def test_postgres_schema_creation() -> None:
    database = PostgresDatabase(
        DatabaseConfig(
            database_url=POSTGRES_DATABASE_URL,
        )
    )

    try:
        schema_manager = PostgresSchemaManager(database)

        await schema_manager.create_all()
    finally:
        await database.close()