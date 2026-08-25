import pytest

from runtime.context.memory_item import MemoryItem
from runtime.memory import MemoryAccessPolicy
from runtime.memory.in_memory_memory_store import InMemoryMemoryStore
from runtime.memory.memory_runtime import MemoryRuntime
from runtime.memory.memory_scope import (
    MemoryScope,
    MemoryScopeType,
)
from runtime.memory.memory_scope_resolver import (
    DefaultMemoryScopeResolver,
)
from tests.runtime.test_agent_runtime import create_runtime_context


# ============================================================
# Scope Resolver
# ============================================================


def test_scope_resolver_returns_scopes_in_order():
    agent_scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    agent_type_scope = MemoryScope(
        type=MemoryScopeType.AGENT_TYPE,
        id="research-agent",
    )

    resolver = DefaultMemoryScopeResolver(
        scopes=[
            agent_scope,
            agent_type_scope,
        ]
    )

    assert resolver.resolve() == [
        agent_scope,
        agent_type_scope,
    ]


def test_scope_resolver_does_not_expose_internal_list():
    agent_scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    resolver = DefaultMemoryScopeResolver(
        scopes=[agent_scope]
    )

    scopes = resolver.resolve()

    scopes.clear()

    assert resolver.resolve() == [
        agent_scope
    ]


# ============================================================
# MemoryRuntime - Write
# ============================================================


@pytest.mark.asyncio
async def test_write_uses_primary_scope_only():
    agent_scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    agent_type_scope = MemoryScope(
        type=MemoryScopeType.AGENT_TYPE,
        id="research-agent",
    )

    store = InMemoryMemoryStore()

    resolver = DefaultMemoryScopeResolver(
        scopes=[
            agent_scope,
            agent_type_scope,
        ]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
    )

    context = create_runtime_context()

    item = MemoryItem(
        content="private research memory"
    )

    await runtime.write(
        item,
        context,
    )

    assert await store.read(
        agent_scope
    ) == [item]

    assert await store.read(
        agent_type_scope
    ) == []


# ============================================================
# MemoryRuntime - Read
# ============================================================


@pytest.mark.asyncio
async def test_read_reads_all_resolved_scopes_in_priority_order():
    agent_scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    agent_type_scope = MemoryScope(
        type=MemoryScopeType.AGENT_TYPE,
        id="research-agent",
    )

    store = InMemoryMemoryStore()

    private_item = MemoryItem(
        content="private memory"
    )

    shared_item = MemoryItem(
        content="shared memory"
    )

    await store.write(
        agent_scope,
        private_item,
    )

    await store.write(
        agent_type_scope,
        shared_item,
    )

    resolver = DefaultMemoryScopeResolver(
        scopes=[
            agent_scope,
            agent_type_scope,
        ]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
    )

    context = create_runtime_context()

    memories = await runtime.read(
        context
    )

    assert memories == [
        private_item,
        shared_item,
    ]


# ============================================================
# MemoryRuntime - Query
# ============================================================


@pytest.mark.asyncio
async def test_query_reads_multiple_scopes_and_respects_limit():
    agent_scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    agent_type_scope = MemoryScope(
        type=MemoryScopeType.AGENT_TYPE,
        id="research-agent",
    )

    store = InMemoryMemoryStore()

    private_1 = MemoryItem(
        content="NVIDIA private research 1"
    )

    private_2 = MemoryItem(
        content="NVIDIA private research 2"
    )

    shared_1 = MemoryItem(
        content="NVIDIA shared research 1"
    )

    shared_2 = MemoryItem(
        content="NVIDIA shared research 2"
    )

    await store.write(
        agent_scope,
        private_1,
    )

    await store.write(
        agent_scope,
        private_2,
    )

    await store.write(
        agent_type_scope,
        shared_1,
    )

    await store.write(
        agent_type_scope,
        shared_2,
    )

    resolver = DefaultMemoryScopeResolver(
        scopes=[
            agent_scope,
            agent_type_scope,
        ]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
    )

    context = create_runtime_context()

    results = await runtime.query(
        "NVIDIA",
        context,
        limit=3,
    )

    assert results == [
        private_1,
        private_2,
        shared_1,
    ]

    assert len(results) == 3


@pytest.mark.asyncio
async def test_query_with_non_positive_limit_returns_empty():
    scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    store = InMemoryMemoryStore()

    item = MemoryItem(
        content="NVIDIA research"
    )

    await store.write(
        scope,
        item,
    )

    resolver = DefaultMemoryScopeResolver(
        scopes=[scope]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
    )

    context = create_runtime_context()

    assert await runtime.query(
        "NVIDIA",
        context,
        limit=0,
    ) == []

    assert await runtime.query(
        "NVIDIA",
        context,
        limit=-1,
    ) == []


# ============================================================
# MemoryRuntime - Forget
# ============================================================


@pytest.mark.asyncio
async def test_forget_finds_memory_across_scopes():
    agent_scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    agent_type_scope = MemoryScope(
        type=MemoryScopeType.AGENT_TYPE,
        id="research-agent",
    )

    store = InMemoryMemoryStore()

    shared_item = MemoryItem(
        content="shared research memory"
    )

    await store.write(
        agent_type_scope,
        shared_item,
    )

    resolver = DefaultMemoryScopeResolver(
        scopes=[
            agent_scope,
            agent_type_scope,
        ]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
        # access_policy=MemoryAccessPolicy(True,True,True)
    )

    context = create_runtime_context()

    await runtime.forget(
        shared_item.id,
        context,
    )

    assert await store.read(
        agent_type_scope
    ) == []


@pytest.mark.asyncio
async def test_forget_deletes_first_matching_scope():
    agent_scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    agent_type_scope = MemoryScope(
        type=MemoryScopeType.AGENT_TYPE,
        id="research-agent",
    )

    store = InMemoryMemoryStore()

    # Deliberately create the same Memory ID in both scopes.
    shared_id = "same-memory-id"

    private_item = MemoryItem(
        id=shared_id,
        content="private memory",
    )

    shared_item = MemoryItem(
        id=shared_id,
        content="shared memory",
    )

    await store.write(
        agent_scope,
        private_item,
    )

    await store.write(
        agent_type_scope,
        shared_item,
    )

    resolver = DefaultMemoryScopeResolver(
        scopes=[
            agent_scope,
            agent_type_scope,
        ]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
        # access_policy=MemoryAccessPolicy(True,True,True)
    )

    context = create_runtime_context()

    await runtime.forget(
        shared_id,
        context,
    )

    assert await store.read(
        agent_scope
    ) == []

    assert await store.read(
        agent_type_scope
    ) == [shared_item]


# ============================================================
# MemoryRuntime - Clear
# ============================================================


@pytest.mark.asyncio
async def test_clear_only_clears_primary_scope():
    agent_scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    agent_type_scope = MemoryScope(
        type=MemoryScopeType.AGENT_TYPE,
        id="research-agent",
    )

    store = InMemoryMemoryStore()

    private_item = MemoryItem(
        content="private memory"
    )

    shared_item = MemoryItem(
        content="shared memory"
    )

    await store.write(
        agent_scope,
        private_item,
    )

    await store.write(
        agent_type_scope,
        shared_item,
    )

    resolver = DefaultMemoryScopeResolver(
        scopes=[
            agent_scope,
            agent_type_scope,
        ]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
        # access_policy=MemoryAccessPolicy(True,True,True)
    )

    context = create_runtime_context()

    await runtime.clear(
        context
    )

    assert await store.read(
        agent_scope
    ) == []

    assert await store.read(
        agent_type_scope
    ) == [shared_item]


# ============================================================
# Empty Scope
# ============================================================


@pytest.mark.asyncio
async def test_write_without_scope_fails():
    store = InMemoryMemoryStore()

    resolver = DefaultMemoryScopeResolver(
        scopes=[]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
    )

    context = create_runtime_context()

    with pytest.raises(
        RuntimeError,
        match="No memory scope is available",
    ):
        await runtime.write(
            MemoryItem(
                content="should fail"
            ),
            context,
        )


@pytest.mark.asyncio
async def test_clear_without_scope_fails():
    store = InMemoryMemoryStore()

    resolver = DefaultMemoryScopeResolver(
        scopes=[]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
        # access_policy=MemoryAccessPolicy(True,True,True)
    )

    context = create_runtime_context()

    with pytest.raises(
        RuntimeError,
        match="No memory scope is available",
    ):
        await runtime.clear(
            context,
        )