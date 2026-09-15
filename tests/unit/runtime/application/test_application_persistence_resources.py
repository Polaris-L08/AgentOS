from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from runtime.application.application import AgentApplication
from runtime.application.application_assembly import ApplicationAssembly
from runtime.application.application_config import ApplicationConfig
from runtime.application.application_lifecycle import ApplicationState
from runtime.persistence.in_memory_execution_store import (
    InMemoryExecutionStore,
)
from runtime.persistence.in_memory_session_store import (
    InMemorySessionStore,
)
from runtime.persistence.persistence_config import PersistenceConfig
from runtime.persistence.persistence_mode import PersistenceMode
from runtime.persistence.postgres_execution_store import (
    PostgresExecutionStore,
)
from runtime.persistence.postgres_session_store import (
    PostgresSessionStore,
)


class MockRuntime:
    """
    Minimal runtime component required by ApplicationAssembly.

    The existing ApplicationAssembly only requires that these
    components are registered. Their internal behavior is irrelevant
    to persistence resource ownership tests.
    """

PostgresURL = "postgresql+asyncpg://agentos:agentos@192.168.0.170:5432/agentos"

def create_config() -> ApplicationConfig:
    return ApplicationConfig(
        application_id="test-application",
        name="Test Application",
    )


def create_assembly(
    persistence_config: PersistenceConfig | None = None,
) -> ApplicationAssembly:
    assembly = ApplicationAssembly(
        config=create_config(),
        persistence_config=persistence_config,
    )

    assembly.register_component(
        "agent_runtime",
        MockRuntime(),
    )

    assembly.register_component(
        "execution_runtime",
        MockRuntime(),
    )

    return assembly


def test_default_in_memory_application_owns_no_persistence_resources() -> None:
    assembly = create_assembly()

    application = assembly.build()

    assert isinstance(
        application.session_store,
        InMemorySessionStore,
    )
    assert isinstance(
        application.execution_store,
        InMemoryExecutionStore,
    )

    assert application._owned_persistence_resources == ()


def test_in_memory_persistence_does_not_create_external_resources() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    assembly = create_assembly(config)

    application = assembly.build()

    assert application._owned_persistence_resources == ()


def test_postgres_persistence_creates_application_owned_resource() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.POSTGRES,
        database={
            "database_url": PostgresURL,
        },
    )

    with patch(
        "runtime.persistence.persistence_store_factory.PostgresDatabase"
    ) as database_class:
        database = database_class.return_value

        application = create_assembly(config).build()

    assert isinstance(
        application.session_store,
        PostgresSessionStore,
    )
    assert isinstance(
        application.execution_store,
        PostgresExecutionStore,
    )

    assert application._owned_persistence_resources == (
        database,
    )

    assert application.session_store._database is database
    assert application.execution_store._database is database


@pytest.mark.asyncio
async def test_application_stop_closes_owned_persistence_resources() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.POSTGRES,
        database={
            "database_url": PostgresURL,
        },
    )

    with patch(
        "runtime.persistence.persistence_store_factory.PostgresDatabase"
    ) as database_class:
        database = database_class.return_value
        database.close = AsyncMock()

        application = create_assembly(config).build()

    application._state = ApplicationState.RUNNING

    await application.stop()

    database.close.assert_awaited_once()

    assert application.state == ApplicationState.STOPPED
    assert application._persistence_resources_closed is True


@pytest.mark.asyncio
async def test_application_stop_does_not_close_external_persistence_stores() -> None:
    session_store = InMemorySessionStore()
    execution_store = InMemoryExecutionStore()

    application = AgentApplication(
        application_id="test-application",
        name="Test Application",
        agent_runtime=MockRuntime(),
        execution_runtime=MockRuntime(),
        session_store=session_store,
        execution_store=execution_store,
        owned_persistence_resources=(),
    )

    application._state = ApplicationState.RUNNING

    await application.stop()

    assert application.state == ApplicationState.STOPPED
    assert application._owned_persistence_resources == ()


@pytest.mark.asyncio
async def test_application_with_explicit_session_store_only_creates_execution_persistence_resource() -> None:
    explicit_session_store = InMemorySessionStore()

    config = PersistenceConfig(
        mode=PersistenceMode.POSTGRES,
        database={
            "database_url": PostgresURL,
        },
    )

    with patch(
        "runtime.persistence.persistence_store_factory.PostgresDatabase"
    ) as database_class:
        database = database_class.return_value

        assembly = create_assembly(config)

        assembly.register_component(
            "session_store",
            explicit_session_store,
        )

        application = assembly.build()

    assert application.session_store is explicit_session_store

    assert isinstance(
        application.execution_store,
        PostgresExecutionStore,
    )

    assert application._owned_persistence_resources == (
        database,
    )

    assert application.execution_store._database is database


@pytest.mark.asyncio
async def test_application_with_explicit_execution_store_only_creates_session_persistence_resource() -> None:
    explicit_execution_store = InMemoryExecutionStore()

    config = PersistenceConfig(
        mode=PersistenceMode.POSTGRES,
        database={
            "database_url": PostgresURL,
        },
    )

    with patch(
        "runtime.persistence.persistence_store_factory.PostgresDatabase"
    ) as database_class:
        database = database_class.return_value

        assembly = create_assembly(config)

        assembly.register_component(
            "execution_store",
            explicit_execution_store,
        )

        application = assembly.build()

    assert application.execution_store is explicit_execution_store

    assert isinstance(
        application.session_store,
        PostgresSessionStore,
    )

    assert application._owned_persistence_resources == (
        database,
    )

    assert application.session_store._database is database


def test_application_with_both_explicit_stores_owns_no_persistence_resources() -> None:
    explicit_session_store = InMemorySessionStore()
    explicit_execution_store = InMemoryExecutionStore()

    config = PersistenceConfig(
        mode=PersistenceMode.POSTGRES,
        database={
            "database_url": PostgresURL,
        },
    )

    with patch(
        "runtime.persistence.persistence_store_factory.PostgresDatabase"
    ) as database_class:
        assembly = create_assembly(config)

        assembly.register_component(
            "session_store",
            explicit_session_store,
        )

        assembly.register_component(
            "execution_store",
            explicit_execution_store,
        )

        application = assembly.build()

    database_class.assert_not_called()

    assert application.session_store is explicit_session_store
    assert application.execution_store is explicit_execution_store
    assert application._owned_persistence_resources == ()


@pytest.mark.asyncio
async def test_application_does_not_close_resources_twice() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.POSTGRES,
        database={
            "database_url": PostgresURL,
        },
    )

    with patch(
        "runtime.persistence.persistence_store_factory.PostgresDatabase"
    ) as database_class:
        database = database_class.return_value
        database.close = AsyncMock()

        application = create_assembly(config).build()

    await application._close_owned_persistence_resources()
    await application._close_owned_persistence_resources()

    database.close.assert_awaited_once()
    assert application._persistence_resources_closed is True