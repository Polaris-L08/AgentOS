from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from runtime.persistence import (
    PostgresSessionStore,
)
from runtime.session.session_state import SessionState


def create_session_state(
    session_id: str,
    metadata: dict[str, Any] | None = None,
) -> SessionState:
    return SessionState(
        session_id=session_id,
        created_at=datetime.now(timezone.utc),
        metadata=metadata or {},
    )


@pytest.mark.asyncio
async def test_save_and_load_session_state(
    session_store: PostgresSessionStore,
) -> None:
    state = create_session_state(
        session_id="session-integration-001",
        metadata={
            "user_id": "user-001",
            "source": "integration-test",
            "preferences": {
                "language": "zh-CN",
                "theme": "dark",
            },
        },
    )

    await session_store.save(state)

    loaded = await session_store.load(state.session_id)

    assert loaded is not None
    assert loaded.session_id == state.session_id
    assert loaded.created_at == state.created_at
    assert loaded.metadata == state.metadata


@pytest.mark.asyncio
async def test_load_missing_session_returns_none(
    session_store: PostgresSessionStore,
) -> None:
    loaded = await session_store.load(
        "session-does-not-exist",
    )

    assert loaded is None


@pytest.mark.asyncio
async def test_save_replaces_existing_session(
    session_store: PostgresSessionStore,
) -> None:
    session_id = "session-integration-replace"

    first_state = create_session_state(
        session_id=session_id,
        metadata={
            "version": 1,
            "value": "first",
        },
    )

    second_state = create_session_state(
        session_id=session_id,
        metadata={
            "version": 2,
            "value": "second",
        },
    )

    await session_store.save(first_state)
    await session_store.save(second_state)

    loaded = await session_store.load(session_id)

    assert loaded is not None
    assert loaded.metadata == second_state.metadata
    assert loaded.created_at == second_state.created_at


@pytest.mark.asyncio
async def test_delete_session(
    session_store: PostgresSessionStore,
) -> None:
    state = create_session_state(
        session_id="session-integration-delete",
    )

    await session_store.save(state)

    assert await session_store.load(state.session_id) is not None

    await session_store.delete(state.session_id)

    assert await session_store.load(state.session_id) is None


@pytest.mark.asyncio
async def test_delete_missing_session_is_safe(
    session_store: PostgresSessionStore,
) -> None:
    await session_store.delete(
        "session-delete-missing",
    )


@pytest.mark.asyncio
async def test_session_metadata_is_persisted_as_independent_data(
    session_store: PostgresSessionStore,
) -> None:
    metadata = {
        "nested": {
            "items": [
                "one",
                "two",
            ],
        },
    }

    state = create_session_state(
        session_id="session-integration-jsonb",
        metadata=metadata,
    )

    await session_store.save(state)

    metadata["nested"]["items"].append("three")

    loaded = await session_store.load(state.session_id)

    assert loaded is not None
    assert loaded.metadata == {
        "nested": {
            "items": [
                "one",
                "two",
            ],
        },
    }