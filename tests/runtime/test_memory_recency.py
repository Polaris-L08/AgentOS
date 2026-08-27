from datetime import datetime, timedelta, timezone

import pytest

from runtime.context.memory_item import MemoryItem
from runtime.context.memory_metadata import MemoryMetadata
from runtime.memory.memory_recency import (
    ExponentialRecencyScorer,
)


def create_memory(
    created_at: datetime,
) -> MemoryItem:

    return MemoryItem(
        content="test memory",
        metadata=MemoryMetadata(
            created_at=created_at,
        ),
    )


def test_new_memory_has_recency_score_one():

    now = datetime.now(timezone.utc)

    memory = create_memory(now)

    scorer = ExponentialRecencyScorer(
        half_life_days=30,
    )

    score = scorer.score(
        memory,
        now=now,
    )

    assert score == pytest.approx(1.0)


def test_half_life_produces_half_score():

    now = datetime.now(timezone.utc)

    created_at = (
        now - timedelta(days=30)
    )

    memory = create_memory(
        created_at
    )

    scorer = ExponentialRecencyScorer(
        half_life_days=30,
    )

    score = scorer.score(
        memory,
        now=now,
    )

    assert score == pytest.approx(
        0.5,
        abs=1e-6,
    )


def test_double_half_life_produces_quarter_score():

    now = datetime.now(timezone.utc)

    created_at = (
        now - timedelta(days=60)
    )

    memory = create_memory(
        created_at
    )

    scorer = ExponentialRecencyScorer(
        half_life_days=30,
    )

    score = scorer.score(
        memory,
        now=now,
    )

    assert score == pytest.approx(
        0.25,
        abs=1e-6,
    )


def test_future_memory_has_score_one():

    now = datetime.now(timezone.utc)

    created_at = (
        now + timedelta(days=1)
    )

    memory = create_memory(
        created_at
    )

    scorer = ExponentialRecencyScorer(
        half_life_days=30,
    )

    score = scorer.score(
        memory,
        now=now,
    )

    assert score == pytest.approx(1.0)


def test_recency_score_decreases_with_age():

    now = datetime.now(timezone.utc)

    recent = create_memory(
        now - timedelta(days=1)
    )

    old = create_memory(
        now - timedelta(days=60)
    )

    scorer = ExponentialRecencyScorer(
        half_life_days=30,
    )

    recent_score = scorer.score(
        recent,
        now=now,
    )

    old_score = scorer.score(
        old,
        now=now,
    )

    assert recent_score > old_score


def test_invalid_half_life_is_rejected():

    with pytest.raises(ValueError):

        ExponentialRecencyScorer(
            half_life_days=0
        )