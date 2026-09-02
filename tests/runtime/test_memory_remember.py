from datetime import datetime, timedelta, timezone

import pytest

from runtime.context.memory_item import MemoryItem, MemorySource
from runtime.context.memory_metadata import MemoryMetadata
from runtime.memory import (
    InMemoryMemoryStore,
    MemoryAccessPolicy,
    MemoryRuntime,
    MemoryScope,
    MemoryScopeType,
)
from runtime.memory.memory_scope_resolver import DefaultMemoryScopeResolver


def create_memory_runtime(
    store: InMemoryMemoryStore | None = None,
    *,
    scopes: list[MemoryScope] | None = None,
    access_policy: MemoryAccessPolicy | None = None,
):
    resolved_scopes = scopes or [
        MemoryScope(
            type=MemoryScopeType.AGENT,
            id="remember-agent",
        )
    ]

    return MemoryRuntime(
        scope_resolver=DefaultMemoryScopeResolver(
            scopes=resolved_scopes,
        ),
        store=store or InMemoryMemoryStore(),
        access_policy=access_policy,
    )


@pytest.mark.asyncio
async def test_remember_creates_and_persists_memory(runtime_context):
    store = InMemoryMemoryStore()
    runtime = create_memory_runtime(store)

    item = await runtime.remember(
        "NVIDIA quarterly revenue increased",
        runtime_context,
    )

    assert isinstance(item, MemoryItem)
    assert item.content == "NVIDIA quarterly revenue increased"
    assert item.importance == 1.0
    assert item.source == MemorySource.HISTORY

    stored = await store.read(
        MemoryScope(
            type=MemoryScopeType.AGENT,
            id="remember-agent",
        )
    )

    assert stored == [item]


@pytest.mark.asyncio
async def test_remember_preserves_importance_source_and_metadata(
    runtime_context,
):
    store = InMemoryMemoryStore()
    runtime = create_memory_runtime(store)

    created_at = datetime.now(timezone.utc) - timedelta(hours=1)
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)

    metadata = MemoryMetadata(
        created_at=created_at,
        expires_at=expires_at,
    )

    item = await runtime.remember(
        "Tool result worth retaining",
        runtime_context,
        importance=0.8,
        source=MemorySource.TOOL,
        metadata=metadata,
    )

    assert item.importance == 0.8
    assert item.source == MemorySource.TOOL
    assert item.metadata == metadata


@pytest.mark.asyncio
async def test_remember_writes_only_to_primary_scope(
    runtime_context,
):
    primary = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="primary-agent",
    )

    shared = MemoryScope(
        type=MemoryScopeType.AGENT_TYPE,
        id="research-agent",
    )

    store = InMemoryMemoryStore()

    runtime = create_memory_runtime(
        store,
        scopes=[primary, shared],
    )

    item = await runtime.remember(
        "Primary scope memory",
        runtime_context,
    )

    assert await store.read(primary) == [item]
    assert await store.read(shared) == []


@pytest.mark.asyncio
async def test_remember_respects_write_access_policy(
    runtime_context,
):
    store = InMemoryMemoryStore()

    runtime = create_memory_runtime(
        store,
        access_policy=MemoryAccessPolicy(
            allow_read=True,
            allow_write=False,
            allow_delete=False,
        ),
    )

    with pytest.raises(PermissionError):
        await runtime.remember(
            "This write must be rejected",
            runtime_context,
        )

    scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="remember-agent",
    )

    assert await store.read(scope) == []


@pytest.mark.asyncio
async def test_remember_returns_the_same_item_written_by_write(
    runtime_context,
):
    store = InMemoryMemoryStore()
    runtime = create_memory_runtime(store)

    item = await runtime.remember(
        "Identity preservation test",
        runtime_context,
    )

    scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="remember-agent",
    )

    stored = await store.read(scope)

    assert len(stored) == 1
    assert stored[0] is item