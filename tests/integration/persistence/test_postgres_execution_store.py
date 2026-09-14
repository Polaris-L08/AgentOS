from __future__ import annotations

from datetime import datetime, timezone

import pytest

from runtime.execution.execution_state import (
    ExecutionState,
    ExecutionStatus,
)
from runtime.persistence import (
    PostgresExecutionStore,
)


def create_execution_state(
    execution_id: str,
    status: ExecutionStatus = ExecutionStatus.CREATED,
    task_id: str = "task-integration-001",
    session_id: str | None = "session-integration-001",
) -> ExecutionState:
    now = datetime.now(timezone.utc)

    return ExecutionState(
        execution_id=execution_id,
        status=status,
        task_id=task_id,
        session_id=session_id,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_save_and_load_execution_state(
    execution_store: PostgresExecutionStore,
) -> None:
    state = create_execution_state(
        execution_id="execution-integration-001",
        status=ExecutionStatus.RUNNING,
    )

    await execution_store.save(state)

    loaded = await execution_store.load(state.execution_id)

    assert loaded is not None
    assert loaded.execution_id == state.execution_id
    assert loaded.status == state.status
    assert loaded.task_id == state.task_id
    assert loaded.session_id == state.session_id
    assert loaded.created_at == state.created_at
    assert loaded.updated_at == state.updated_at


@pytest.mark.asyncio
async def test_load_missing_execution_returns_none(
    execution_store: PostgresExecutionStore,
) -> None:
    loaded = await execution_store.load(
        "execution-does-not-exist",
    )

    assert loaded is None


@pytest.mark.asyncio
async def test_save_replaces_existing_execution(
    execution_store: PostgresExecutionStore,
) -> None:
    execution_id = "execution-integration-replace"

    first_state = create_execution_state(
        execution_id=execution_id,
        status=ExecutionStatus.CREATED,
    )

    second_state = create_execution_state(
        execution_id=execution_id,
        status=ExecutionStatus.COMPLETED,
    )

    await execution_store.save(first_state)
    await execution_store.save(second_state)

    loaded = await execution_store.load(execution_id)

    assert loaded is not None
    assert loaded.status == ExecutionStatus.COMPLETED
    assert loaded.task_id == second_state.task_id
    assert loaded.session_id == second_state.session_id
    assert loaded.created_at == second_state.created_at
    assert loaded.updated_at == second_state.updated_at


@pytest.mark.asyncio
async def test_delete_execution(
    execution_store: PostgresExecutionStore,
) -> None:
    state = create_execution_state(
        execution_id="execution-integration-delete",
    )

    await execution_store.save(state)

    assert await execution_store.load(state.execution_id) is not None

    await execution_store.delete(state.execution_id)

    assert await execution_store.load(state.execution_id) is None


@pytest.mark.asyncio
async def test_delete_missing_execution_is_safe(
    execution_store: PostgresExecutionStore,
) -> None:
    await execution_store.delete(
        "execution-delete-missing",
    )


@pytest.mark.asyncio
async def test_execution_with_null_session_id(
    execution_store: PostgresExecutionStore,
) -> None:
    state = create_execution_state(
        execution_id="execution-integration-null-session",
        session_id=None,
    )

    await execution_store.save(state)

    loaded = await execution_store.load(state.execution_id)

    assert loaded is not None
    assert loaded.session_id is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        ExecutionStatus.CREATED,
        ExecutionStatus.RUNNING,
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.PAUSED,
    ],
)
async def test_execution_status_round_trip(
    execution_store: PostgresExecutionStore,
    status: ExecutionStatus,
) -> None:
    state = create_execution_state(
        execution_id=f"execution-status-{status.value}",
        status=status,
    )

    await execution_store.save(state)

    loaded = await execution_store.load(state.execution_id)

    assert loaded is not None
    assert loaded.status == status