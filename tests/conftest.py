from __future__ import annotations

import os

import pytest
import pytest_asyncio

from runtime.events.event_bus import EventBus
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.persistence.database_config import DatabaseConfig
from runtime.persistence.postgres import PostgresDatabase
from runtime.persistence.postgres_execution_store import PostgresExecutionStore
from runtime.persistence.schema import PostgresSchemaManager
# from runtime.persistence import PostgresDatabase, DatabaseConfig, PostgresSchemaManager, PostgresExecutionStore
from runtime.tracing.trace_recorder import TraceRecorder

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.fixture
def event_bus():

    return EventBus()



@pytest.fixture
def runtime_context():
    trace_recorder = TraceRecorder()
    execution_runtime = ExecutionRuntime(trace_recorder)
    runtime_context = execution_runtime.create_context()
    return runtime_context

POSTGRES_DATABASE_URL = os.getenv(
    "AGENTOS_TEST_DATABASE_URL",
    "postgresql+asyncpg://agentos:agentos@192.168.0.170:5432/agentos",
)

@pytest_asyncio.fixture
async def postgres_database() -> PostgresDatabase:
    database = PostgresDatabase(
        DatabaseConfig(
            database_url=POSTGRES_DATABASE_URL,
        )
    )

    schema_manager = PostgresSchemaManager(database)
    await schema_manager.create_all()

    try:
        yield database
    finally:
        await database.close()


@pytest_asyncio.fixture
async def execution_store(
    postgres_database: PostgresDatabase,
) -> PostgresExecutionStore:
    return PostgresExecutionStore(postgres_database)