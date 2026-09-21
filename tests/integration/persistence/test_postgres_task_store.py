from __future__ import annotations

import pytest

from models.task_request import TaskRequest
from runtime.persistence import PostgresTaskStore


def create_task(
    task_id: str,
    user_input: str = "analyze NVIDIA",
    session_id: str | None = "session-integration-001",
) -> TaskRequest:
    return TaskRequest(
        task_id=task_id,
        user_input=user_input,
        session_id=session_id,
    )


@pytest.fixture
def task_store(postgres_database):
    return PostgresTaskStore(postgres_database)


@pytest.mark.asyncio
async def test_save_and_load_task(
    task_store: PostgresTaskStore,
) -> None:
    task = create_task(
        task_id="task-integration-001",
        user_input="analyze NVIDIA risk",
        session_id="session-integration-001",
    )

    await task_store.save(task)

    loaded = await task_store.load(task.task_id)

    assert loaded is not None
    assert loaded.task_id == task.task_id
    assert loaded.user_input == task.user_input
    assert loaded.session_id == task.session_id


@pytest.mark.asyncio
async def test_load_missing_task_returns_none(
    task_store: PostgresTaskStore,
) -> None:
    loaded = await task_store.load(
        "task-does-not-exist",
    )

    assert loaded is None


@pytest.mark.asyncio
async def test_save_replaces_existing_task(
    task_store: PostgresTaskStore,
) -> None:
    task_id = "task-integration-replace"

    first_task = create_task(
        task_id=task_id,
        user_input="first request",
        session_id="session-first",
    )

    second_task = create_task(
        task_id=task_id,
        user_input="second request",
        session_id="session-second",
    )

    await task_store.save(first_task)
    await task_store.save(second_task)

    loaded = await task_store.load(task_id)

    assert loaded is not None
    assert loaded.task_id == task_id
    assert loaded.user_input == second_task.user_input
    assert loaded.session_id == second_task.session_id


@pytest.mark.asyncio
async def test_delete_task(
    task_store: PostgresTaskStore,
) -> None:
    task = create_task(
        task_id="task-integration-delete",
    )

    await task_store.save(task)

    loaded = await task_store.load(task.task_id)
    assert loaded is not None

    await task_store.delete(task.task_id)

    loaded_after_delete = await task_store.load(
        task.task_id,
    )

    assert loaded_after_delete is None


@pytest.mark.asyncio
async def test_delete_missing_task_is_safe(
    task_store: PostgresTaskStore,
) -> None:
    await task_store.delete(
        "task-delete-missing",
    )

    loaded = await task_store.load(
        "task-delete-missing",
    )

    assert loaded is None


@pytest.mark.asyncio
async def test_task_is_persisted_independently_from_original_object(
    task_store: PostgresTaskStore,
) -> None:
    task = create_task(
        task_id="task-integration-independent",
        user_input="original request",
        session_id="session-original",
    )

    await task_store.save(task)

    # task.user_input = "modified after save"
    # task.session_id = "session-modified"

    task_modified = create_task(
        task_id="task-integration-independent",
        user_input="modified after save",
        session_id="session-modified",
    )

    loaded = await task_store.load(task_modified.task_id)

    assert loaded is not None
    assert loaded.user_input == "original request"
    assert loaded.session_id == "session-original"