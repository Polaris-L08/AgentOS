from __future__ import annotations

from datetime import datetime, timezone

import pytest

from runtime.execution.execution_state import ExecutionState, ExecutionStatus
from runtime.persistence.in_memory_execution_store import InMemoryExecutionStore


@pytest.mark.asyncio
async def test_save_and_load() -> None:
    store = InMemoryExecutionStore()

    state = ExecutionState(
        execution_id="E001",
        status=ExecutionStatus.CREATED,
        task_id="T001",
        session_id="S001",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        metadata={"application": "test"},
    )

    await store.save(state)

    loaded = await store.load("E001")

    assert loaded == state


@pytest.mark.asyncio
async def test_load_missing_execution_returns_none() -> None:
    store = InMemoryExecutionStore()

    loaded = await store.load("E001")

    assert loaded is None


@pytest.mark.asyncio
async def test_save_replaces_existing_state() -> None:
    store = InMemoryExecutionStore()

    now = datetime.now(timezone.utc)

    first = ExecutionState(
        execution_id="E001",
        status=ExecutionStatus.CREATED,
        task_id="T001",
        session_id="S001",
        created_at=now,
        updated_at=now,
    )

    second = ExecutionState(
        execution_id="E001",
        status=ExecutionStatus.RUNNING,
        task_id="T001",
        session_id="S001",
        created_at=now,
        updated_at=now,
    )

    await store.save(first)
    await store.save(second)

    loaded = await store.load("E001")

    assert loaded == second


@pytest.mark.asyncio
async def test_delete_removes_execution() -> None:
    store = InMemoryExecutionStore()

    now = datetime.now(timezone.utc)

    state = ExecutionState(
        execution_id="E001",
        status=ExecutionStatus.CREATED,
        task_id="T001",
        session_id="S001",
        created_at=now,
        updated_at=now,
    )

    await store.save(state)

    await store.delete("E001")

    assert await store.load("E001") is None


@pytest.mark.asyncio
async def test_delete_missing_execution_is_safe() -> None:
    store = InMemoryExecutionStore()

    await store.delete("E001")


@pytest.mark.asyncio
async def test_save_does_not_share_state_with_store() -> None:
    store = InMemoryExecutionStore()

    now = datetime.now(timezone.utc)

    state = ExecutionState(
        execution_id="E001",
        status=ExecutionStatus.CREATED,
        task_id="T001",
        session_id="S001",
        created_at=now,
        updated_at=now,
        metadata={"key": "value"},
    )

    await store.save(state)

    state.metadata["key"] = "changed"

    loaded = await store.load("E001")

    assert loaded is not None
    assert loaded.metadata["key"] == "value"


@pytest.mark.asyncio
async def test_load_does_not_expose_store_state() -> None:
    store = InMemoryExecutionStore()

    now = datetime.now(timezone.utc)

    state = ExecutionState(
        execution_id="E001",
        status=ExecutionStatus.CREATED,
        task_id="T001",
        session_id="S001",
        created_at=now,
        updated_at=now,
        metadata={"key": "value"},
    )

    await store.save(state)

    loaded = await store.load("E001")

    assert loaded is not None

    loaded.metadata["key"] = "changed"

    loaded_again = await store.load("E001")

    assert loaded_again is not None
    assert loaded_again.metadata["key"] == "value"