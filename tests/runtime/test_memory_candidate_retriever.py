from datetime import datetime, timedelta, timezone

from runtime.context.memory_item import MemoryItem
from runtime.context.memory_metadata import MemoryMetadata
from runtime.memory.memory_candidate_retriever import (
    KeywordMemoryCandidateRetriever,
)


def test_keyword_candidate_retriever_returns_matching_memories():

    first = MemoryItem(
        content="NVIDIA revenue increased",
    )

    second = MemoryItem(
        content="Apple revenue increased",
    )

    retriever = KeywordMemoryCandidateRetriever()

    result = retriever.retrieve(
        [
            first,
            second,
        ],
        "NVIDIA",
    )

    assert result == [
        first,
    ]


def test_keyword_candidate_retriever_does_not_rank():

    low = MemoryItem(
        content="NVIDIA low",
        importance=0.1,
    )

    high = MemoryItem(
        content="NVIDIA high",
        importance=1.0,
    )

    retriever = KeywordMemoryCandidateRetriever()

    result = retriever.retrieve(
        [
            low,
            high,
        ],
        "NVIDIA",
    )

    assert result == [
        low,
        high,
    ]


def test_keyword_candidate_retriever_does_not_apply_limit():

    memories = [
        MemoryItem(
            content=f"NVIDIA memory {index}",
        )
        for index in range(20)
    ]

    retriever = KeywordMemoryCandidateRetriever()

    result = retriever.retrieve(
        memories,
        "NVIDIA",
    )

    assert len(result) == 20


def test_keyword_candidate_retriever_excludes_expired_memories():

    now = datetime.now(timezone.utc)

    expired = MemoryItem(
        content="NVIDIA expired",
        metadata=MemoryMetadata(
            created_at=now - timedelta(days=2),
            expires_at=now - timedelta(days=1),
        ),
    )

    active = MemoryItem(
        content="NVIDIA active",
        metadata=MemoryMetadata(
            created_at=now,
            expires_at=now + timedelta(days=1),
        ),
    )

    retriever = KeywordMemoryCandidateRetriever()

    result = retriever.retrieve(
        [
            expired,
            active,
        ],
        "NVIDIA",
    )

    assert result == [
        active,
    ]


def test_empty_query_returns_all_active_memories():

    first = MemoryItem(
        content="NVIDIA",
    )

    second = MemoryItem(
        content="Apple",
    )

    retriever = KeywordMemoryCandidateRetriever()

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