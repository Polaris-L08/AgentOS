import pytest

from runtime.context.memory_item import MemoryItem, MemorySource
from runtime.memory.in_memory_memory_store import (
    InMemoryMemoryStore,
)
from runtime.memory.memory_query import MemoryQuery
from runtime.memory.memory_runtime import MemoryRuntime
from runtime.memory.memory_scope import (
    MemoryScope,
    MemoryScopeType,
)
from runtime.memory.memory_scope_resolver import (
    DefaultMemoryScopeResolver,
)


class RecordingRetriever:
    """
    Retriever used to verify the candidate set received
    from MemoryRuntime.
    """

    def __init__(self):
        self.memories = None
        self.query = None
        self.limit = None

    def retrieve(
        self,
        memories,
        query,
        limit=10,
    ):
        self.memories = list(memories)
        self.query = query
        self.limit = limit

        return memories[:limit]


@pytest.mark.asyncio
async def test_memory_runtime_query_applies_memory_query_before_retrieval(runtime_context):

    scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    store = InMemoryMemoryStore()

    matching = MemoryItem(
        content="NVIDIA important research",
        importance=0.9,
    )

    low_importance = MemoryItem(
        content="NVIDIA low importance",
        importance=0.2,
    )

    unrelated = MemoryItem(
        content="Apple research",
        importance=0.9,
    )

    await store.write(
        scope,
        matching,
    )

    await store.write(
        scope,
        low_importance,
    )

    await store.write(
        scope,
        unrelated,
    )

    retriever = RecordingRetriever()

    runtime = MemoryRuntime(
        scope_resolver=DefaultMemoryScopeResolver(
            scopes=[scope]
        ),
        store=store,
        retriever=retriever,
    )

    # context = create_runtime_context()

    result = await runtime.query(
        "NVIDIA",
        runtime_context,
        memory_query=MemoryQuery(
            min_importance=0.8,
        ),
    )

    assert result == [
        matching,
    ]

    assert retriever.memories == [
        matching,
    ]

    assert retriever.query == "NVIDIA"
    assert retriever.limit == 10


@pytest.mark.asyncio
async def test_memory_runtime_query_filters_source_before_retrieval(runtime_context):

    scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    store = InMemoryMemoryStore()

    history = MemoryItem(
        content="NVIDIA history",
    )

    reflection = MemoryItem(
        content="NVIDIA reflection",
        source=MemorySource.REFLECTION,
    )

    await store.write(
        scope,
        history,
    )

    await store.write(
        scope,
        reflection,
    )

    retriever = RecordingRetriever()

    runtime = MemoryRuntime(
        scope_resolver=DefaultMemoryScopeResolver(
            scopes=[scope]
        ),
        store=store,
        retriever=retriever,
    )

    # context = create_runtime_context()

    result = await runtime.query(
        "NVIDIA",
        runtime_context,
        memory_query=MemoryQuery(
            source=MemorySource.REFLECTION,
        ),
    )

    assert result == [
        reflection,
    ]

    assert retriever.memories == [
        reflection,
    ]


@pytest.mark.asyncio
async def test_memory_runtime_query_filters_expired_before_retrieval(runtime_context):

    from datetime import datetime, timedelta, timezone

    from runtime.context.memory_metadata import (
        MemoryMetadata,
    )

    scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    store = InMemoryMemoryStore()

    now = datetime.now(timezone.utc)

    active = MemoryItem(
        content="NVIDIA active",
        metadata=MemoryMetadata(
            created_at=now,
            expires_at=now + timedelta(hours=1),
        ),
    )

    expired = MemoryItem(
        content="NVIDIA expired",
        metadata=MemoryMetadata(
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        ),
    )

    await store.write(
        scope,
        active,
    )

    await store.write(
        scope,
        expired,
    )

    retriever = RecordingRetriever()

    runtime = MemoryRuntime(
        scope_resolver=DefaultMemoryScopeResolver(
            scopes=[scope]
        ),
        store=store,
        retriever=retriever,
    )

    # context = create_runtime_context()

    result = await runtime.query(
        "NVIDIA",
        runtime_context,
        memory_query=MemoryQuery(),
    )

    assert result == [
        active,
    ]

    assert retriever.memories == [
        active,
    ]


@pytest.mark.asyncio
async def test_memory_runtime_query_keeps_global_limit_after_filtering(runtime_context):

    agent_scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    agent_type_scope = MemoryScope(
        type=MemoryScopeType.AGENT_TYPE,
        id="research-agent",
    )

    store = InMemoryMemoryStore()

    agent_items = [
        MemoryItem(
            content=f"NVIDIA agent {index}",
            importance=0.5,
        )
        for index in range(3)
    ]

    shared_items = [
        MemoryItem(
            content=f"NVIDIA shared {index}",
            importance=0.9,
        )
        for index in range(3)
    ]

    for item in agent_items:
        await store.write(
            agent_scope,
            item,
        )

    for item in shared_items:
        await store.write(
            agent_type_scope,
            item,
        )

    retriever = RecordingRetriever()

    runtime = MemoryRuntime(
        scope_resolver=DefaultMemoryScopeResolver(
            scopes=[
                agent_scope,
                agent_type_scope,
            ]
        ),
        store=store,
        retriever=retriever,
    )

    # context = create_runtime_context()

    result = await runtime.query(
        "NVIDIA",
        runtime_context,
        limit=2,
        memory_query=MemoryQuery(
            min_importance=0.5,
            limit=2,
        ),
    )

    # The Store-level limit must not truncate each scope.
    assert len(retriever.memories) == 6

    # Final limit is applied by the Retriever.
    assert len(result) == 2

    assert result == [
        agent_items[0],
        agent_items[1],
    ]


@pytest.mark.asyncio
async def test_memory_runtime_query_without_memory_query_preserves_behavior(runtime_context):

    scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    store = InMemoryMemoryStore()

    first = MemoryItem(
        content="NVIDIA first",
    )

    second = MemoryItem(
        content="Apple second",
    )

    await store.write(
        scope,
        first,
    )

    await store.write(
        scope,
        second,
    )

    retriever = RecordingRetriever()

    runtime = MemoryRuntime(
        scope_resolver=DefaultMemoryScopeResolver(
            scopes=[scope]
        ),
        store=store,
        retriever=retriever,
    )

    # context = create_runtime_context()

    result = await runtime.query(
        "NVIDIA",
        runtime_context,
    )

    assert result == [
        first,
        second,
    ]

    assert retriever.memories == [
        first,
        second,
    ]