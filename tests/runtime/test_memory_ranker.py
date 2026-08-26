from runtime.context.memory_item import MemoryItem
from runtime.memory.memory_ranker import (
    ImportanceMemoryRanker,
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