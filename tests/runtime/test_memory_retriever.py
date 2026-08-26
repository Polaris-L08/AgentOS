import pytest

from runtime.context.memory_item import MemoryItem
from runtime.memory.in_memory_memory_store import InMemoryMemoryStore
from runtime.memory.memory_retriever import (
    KeywordMemoryRetriever,
)
from runtime.memory.memory_runtime import MemoryRuntime
from runtime.memory.memory_scope import (
    MemoryScope,
    MemoryScopeType,
)
from runtime.memory.memory_scope_resolver import (
    DefaultMemoryScopeResolver,
)


# ============================================================
# KeywordMemoryRetriever
# ============================================================


def test_keyword_retriever_matches_case_insensitively():

    retriever = KeywordMemoryRetriever()

    item = MemoryItem(
        content="NVIDIA quarterly revenue increased"
    )

    result = retriever.retrieve(
        [item],
        "nvidia",
    )

    assert result == [item]


def test_keyword_retriever_returns_only_matching_items():

    retriever = KeywordMemoryRetriever()

    nvidia = MemoryItem(
        content="NVIDIA research"
    )

    apple = MemoryItem(
        content="Apple research"
    )

    result = retriever.retrieve(
        [
            nvidia,
            apple,
        ],
        "nvidia",
    )

    assert result == [nvidia]


def test_keyword_retriever_respects_limit():

    retriever = KeywordMemoryRetriever()

    items = [
        MemoryItem(
            content=f"NVIDIA research {index}"
        )
        for index in range(5)
    ]

    result = retriever.retrieve(
        items,
        "nvidia",
        limit=2,
    )

    assert result == items[:2]


def test_keyword_retriever_non_positive_limit_returns_empty():

    retriever = KeywordMemoryRetriever()

    item = MemoryItem(
        content="NVIDIA research"
    )

    assert retriever.retrieve(
        [item],
        "nvidia",
        limit=0,
    ) == []

    assert retriever.retrieve(
        [item],
        "nvidia",
        limit=-1,
    ) == []


def test_keyword_retriever_empty_query_returns_original_order():

    retriever = KeywordMemoryRetriever()

    first = MemoryItem(
        content="first"
    )

    second = MemoryItem(
        content="second"
    )

    result = retriever.retrieve(
        [
            first,
            second,
        ],
        "",
    )

    assert result == [
        first,
        second,
    ]


# ============================================================
# MemoryRuntime Retrieval Integration
# ============================================================


@pytest.mark.asyncio
async def test_memory_runtime_query_uses_retriever(runtime_context):

    scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    store = InMemoryMemoryStore()

    matching = MemoryItem(
        content="NVIDIA research"
    )

    non_matching = MemoryItem(
        content="Apple research"
    )

    await store.write(
        scope,
        matching,
    )

    await store.write(
        scope,
        non_matching,
    )

    resolver = DefaultMemoryScopeResolver(
        scopes=[scope]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
    )

    # context = create_runtime_context()

    result = await runtime.query(
        "nvidia",
        runtime_context,
    )

    assert result == [
        matching
    ]


@pytest.mark.asyncio
async def test_memory_runtime_query_retrieves_across_scopes(runtime_context):

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
        content="NVIDIA private research"
    )

    shared_item = MemoryItem(
        content="NVIDIA shared research"
    )

    unrelated_item = MemoryItem(
        content="Apple shared research"
    )

    await store.write(
        agent_scope,
        private_item,
    )

    await store.write(
        agent_type_scope,
        shared_item,
    )

    await store.write(
        agent_type_scope,
        unrelated_item,
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

    # context = create_runtime_context()

    result = await runtime.query(
        "NVIDIA",
        runtime_context,
    )

    assert result == [
        private_item,
        shared_item,
    ]


@pytest.mark.asyncio
async def test_memory_runtime_query_limit_is_global(runtime_context):

    agent_scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    agent_type_scope = MemoryScope(
        type=MemoryScopeType.AGENT_TYPE,
        id="research-agent",
    )

    store = InMemoryMemoryStore()

    private_items = [
        MemoryItem(
            content=f"NVIDIA private {index}"
        )
        for index in range(3)
    ]

    shared_items = [
        MemoryItem(
            content=f"NVIDIA shared {index}"
        )
        for index in range(3)
    ]

    for item in private_items:
        await store.write(
            agent_scope,
            item,
        )

    for item in shared_items:
        await store.write(
            agent_type_scope,
            item,
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

    # context = create_runtime_context()

    result = await runtime.query(
        "NVIDIA",
        runtime_context,
        limit=4,
    )

    assert result == [
        private_items[0],
        private_items[1],
        private_items[2],
        shared_items[0],
    ]

    assert len(result) == 4


# ============================================================
# Custom Retriever
# ============================================================


class FirstMemoryRetriever:

    def retrieve(
        self,
        memories: list[MemoryItem],
        query: str,
        limit: int = 10,
    ) -> list[MemoryItem]:

        return memories[:limit]


@pytest.mark.asyncio
async def test_memory_runtime_accepts_custom_retriever(runtime_context):

    scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    store = InMemoryMemoryStore()

    first = MemoryItem(
        content="Apple research"
    )

    second = MemoryItem(
        content="NVIDIA research"
    )

    await store.write(
        scope,
        first,
    )

    await store.write(
        scope,
        second,
    )

    resolver = DefaultMemoryScopeResolver(
        scopes=[scope]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
        retriever=FirstMemoryRetriever(),
    )

    # context = create_runtime_context()

    result = await runtime.query(
        "NVIDIA",
        runtime_context,
    )

    # The custom retriever deliberately ignores the query.
    assert result == [
        first,
        second,
    ]

# =========================================================
# Lesson 8 Test
# =========================================================

def test_keyword_retriever_excludes_expired_memory():

    from datetime import datetime, timedelta, timezone

    from runtime.context.memory_metadata import MemoryMetadata

    retriever = KeywordMemoryRetriever()

    now = datetime.now(timezone.utc)

    active = MemoryItem(
        content="NVIDIA active research",
        metadata=MemoryMetadata(
            created_at=now,
            expires_at=now + timedelta(
                hours=1
            ),
        ),
    )

    expired = MemoryItem(
        content="NVIDIA expired research",
        metadata=MemoryMetadata(
            created_at=now - timedelta(
                hours=2
            ),
            expires_at=now - timedelta(
                hours=1
            ),
        ),
    )

    result = retriever.retrieve(
        [
            active,
            expired,
        ],
        "NVIDIA",
    )

    assert result == [
        active
    ]

def test_keyword_retriever_excludes_expired_memory_for_empty_query():

    from datetime import datetime, timedelta, timezone

    from runtime.context.memory_metadata import MemoryMetadata

    retriever = KeywordMemoryRetriever()

    now = datetime.now(timezone.utc)

    active = MemoryItem(
        content="active memory",
        metadata=MemoryMetadata(
            created_at=now,
            expires_at=now + timedelta(
                hours=1
            ),
        ),
    )

    expired = MemoryItem(
        content="expired memory",
        metadata=MemoryMetadata(
            created_at=now - timedelta(
                hours=2
            ),
            expires_at=now - timedelta(
                hours=1
            ),
        ),
    )

    result = retriever.retrieve(
        [
            active,
            expired,
        ],
        "",
    )

    assert result == [
        active
    ]

@pytest.mark.asyncio
async def test_memory_runtime_query_excludes_expired_memory(runtime_context):

    from datetime import datetime, timedelta, timezone

    from runtime.context.memory_metadata import MemoryMetadata

    scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    store = InMemoryMemoryStore()

    now = datetime.now(timezone.utc)

    active = MemoryItem(
        content="NVIDIA active research",
        metadata=MemoryMetadata(
            created_at=now,
            expires_at=now + timedelta(
                hours=1
            ),
        ),
    )

    expired = MemoryItem(
        content="NVIDIA expired research",
        metadata=MemoryMetadata(
            created_at=now - timedelta(
                hours=2
            ),
            expires_at=now - timedelta(
                hours=1
            ),
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

    resolver = DefaultMemoryScopeResolver(
        scopes=[scope]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
    )

    result = await runtime.query(
        "NVIDIA",
        runtime_context,
    )

    assert result == [
        active
    ]

@pytest.mark.asyncio
async def test_memory_runtime_read_returns_expired_memory(runtime_context):

    from datetime import datetime, timedelta, timezone

    from runtime.context.memory_metadata import MemoryMetadata

    scope = MemoryScope(
        type=MemoryScopeType.AGENT,
        id="research-001",
    )

    store = InMemoryMemoryStore()

    now = datetime.now(timezone.utc)

    active = MemoryItem(
        content="active memory",
        metadata=MemoryMetadata(
            created_at=now,
            expires_at=now + timedelta(
                hours=1
            ),
        ),
    )

    expired = MemoryItem(
        content="expired memory",
        metadata=MemoryMetadata(
            created_at=now - timedelta(
                hours=2
            ),
            expires_at=now - timedelta(
                hours=1
            ),
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

    resolver = DefaultMemoryScopeResolver(
        scopes=[scope]
    )

    runtime = MemoryRuntime(
        scope_resolver=resolver,
        store=store,
    )

    # context = create_runtime_context()

    result = await runtime.read(
        runtime_context
    )

    assert result == [
        active,
        expired,
    ]