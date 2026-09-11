from __future__ import annotations

from datetime import datetime, timezone

import pytest

from runtime.persistence.in_memory_session_store import InMemorySessionStore
from runtime.session.session_state import SessionState


@pytest.mark.asyncio
async def test_save_and_load() -> None:
    store = InMemorySessionStore()

    state = SessionState(
        session_id="S001",
        created_at=datetime.now(timezone.utc),
        metadata={"application": "test"},
    )

    await store.save(state)

    loaded = await store.load("S001")

    assert loaded == state


@pytest.mark.asyncio
async def test_load_missing_session_returns_none() -> None:
    store = InMemorySessionStore()

    loaded = await store.load("S001")

    assert loaded is None


@pytest.mark.asyncio
async def test_save_replaces_existing_state() -> None:
    store = InMemorySessionStore()

    created_at = datetime.now(timezone.utc)

    first = SessionState(
        session_id="S001",
        created_at=created_at,
        metadata={"version": 1},
    )

    second = SessionState(
        session_id="S001",
        created_at=created_at,
        metadata={"version": 2},
    )

    await store.save(first)
    await store.save(second)

    loaded = await store.load("S001")

    assert loaded == second


@pytest.mark.asyncio
async def test_delete_removes_session() -> None:
    store = InMemorySessionStore()

    state = SessionState(
        session_id="S001",
        created_at=datetime.now(timezone.utc),
    )

    await store.save(state)

    await store.delete("S001")

    assert await store.load("S001") is None


@pytest.mark.asyncio
async def test_delete_missing_session_is_safe() -> None:
    store = InMemorySessionStore()

    await store.delete("S001")


@pytest.mark.asyncio
async def test_save_does_not_share_state_with_store() -> None:
    store = InMemorySessionStore()

    state = SessionState(
        session_id="S001",
        created_at=datetime.now(timezone.utc),
        metadata={"key": "value"},
    )

    await store.save(state)

    state.metadata["key"] = "changed"

    loaded = await store.load("S001")

    assert loaded is not None
    assert loaded.metadata["key"] == "value"


@pytest.mark.asyncio
async def test_load_does_not_expose_store_state() -> None:
    store = InMemorySessionStore()

    state = SessionState(
        session_id="S001",
        created_at=datetime.now(timezone.utc),
        metadata={"key": "value"},
    )

    await store.save(state)

    loaded = await store.load("S001")

    assert loaded is not None

    loaded.metadata["key"] = "changed"

    loaded_again = await store.load("S001")

    assert loaded_again is not None
    assert loaded_again.metadata["key"] == "value"