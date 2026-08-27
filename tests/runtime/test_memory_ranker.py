from runtime.context.memory_item import MemoryItem
from runtime.memory.memory_ranker import (
    ImportanceMemoryRanker,
)
from datetime import datetime, timedelta, timezone

from runtime.context.memory_metadata import MemoryMetadata
from runtime.memory.memory_ranker import (
    ImportanceRecencyMemoryRanker,
)


def test_importance_ranker_orders_by_importance():

    low = MemoryItem(
        content="low importance",
        importance=0.2,
    )

    high = MemoryItem(
        content="high importance",
        importance=0.9,
    )

    medium = MemoryItem(
        content="medium importance",
        importance=0.5,
    )

    ranker = ImportanceMemoryRanker()

    result = ranker.rank(
        [
            low,
            high,
            medium,
        ],
        "importance",
    )

    assert result == [
        high,
        medium,
        low,
    ]


def test_importance_ranker_does_not_modify_input():

    first = MemoryItem(
        content="first",
        importance=0.1,
    )

    second = MemoryItem(
        content="second",
        importance=0.9,
    )

    memories = [
        first,
        second,
    ]

    ranker = ImportanceMemoryRanker()

    result = ranker.rank(
        memories,
        "test",
    )

    assert memories == [
        first,
        second,
    ]

    assert result == [
        second,
        first,
    ]


def test_importance_ranker_preserves_order_for_equal_importance():

    first = MemoryItem(
        content="first",
        importance=1.0,
    )

    second = MemoryItem(
        content="second",
        importance=1.0,
    )

    ranker = ImportanceMemoryRanker()

    result = ranker.rank(
        [
            first,
            second,
        ],
        "test",
    )

    assert result == [
        first,
        second,
    ]


def test_importance_ranker_handles_empty_list():

    ranker = ImportanceMemoryRanker()

    result = ranker.rank(
        [],
        "test",
    )

    assert result == []

# =========================================================
# Test ImportanceRecencyMemoryRanker
# =========================================================

def test_importance_recency_ranker_combines_importance_and_recency():

    now = datetime.now(timezone.utc)

    recent = MemoryItem(
        content="recent",
        importance=0.5,
        metadata=MemoryMetadata(
            created_at=now,
        ),
    )

    old = MemoryItem(
        content="old",
        importance=1.0,
        metadata=MemoryMetadata(
            created_at=now - timedelta(days=60),
        ),
    )

    ranker = ImportanceRecencyMemoryRanker(
        importance_weight=0.5,
        recency_weight=0.5,
    )

    result = ranker.rank(
        [
            old,
            recent,
        ],
        "test",
    )

    assert result == [
        recent,
        old,
    ]

def test_importance_recency_ranker_can_prioritize_importance():

    now = datetime.now(timezone.utc)

    important_old = MemoryItem(
        content="important old",
        importance=1.0,
        metadata=MemoryMetadata(
            created_at=now - timedelta(days=60),
        ),
    )

    recent_low = MemoryItem(
        content="recent low",
        importance=0.2,
        metadata=MemoryMetadata(
            created_at=now,
        ),
    )

    ranker = ImportanceRecencyMemoryRanker(
        importance_weight=0.9,
        recency_weight=0.1,
    )

    result = ranker.rank(
        [
            recent_low,
            important_old,
        ],
        "test",
    )

    assert result == [
        important_old,
        recent_low,
    ]

def test_importance_recency_ranker_can_prioritize_recency():

    now = datetime.now(timezone.utc)

    important_old = MemoryItem(
        content="important old",
        importance=1.0,
        metadata=MemoryMetadata(
            created_at=now - timedelta(days=60),
        ),
    )

    recent_low = MemoryItem(
        content="recent low",
        importance=0.2,
        metadata=MemoryMetadata(
            created_at=now,
        ),
    )

    ranker = ImportanceRecencyMemoryRanker(
        importance_weight=0.1,
        recency_weight=0.9,
    )

    result = ranker.rank(
        [
            important_old,
            recent_low,
        ],
        "test",
    )

    assert result == [
        recent_low,
        important_old,
    ]

import pytest

def test_ranker_rejects_negative_weights():

    with pytest.raises(ValueError):

        ImportanceRecencyMemoryRanker(
            importance_weight=-1,
            recency_weight=1,
        )


def test_ranker_rejects_zero_weights():

    with pytest.raises(ValueError):

        ImportanceRecencyMemoryRanker(
            importance_weight=0,
            recency_weight=0,
        )