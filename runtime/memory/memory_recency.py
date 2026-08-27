from datetime import datetime, timezone
from math import exp
from typing import Protocol

from runtime.context.memory_item import MemoryItem


class MemoryRecencyScorer(Protocol):
    """
    Strategy for calculating the recency score of a MemoryItem.

    The returned score must be normalized to [0.0, 1.0].
    """

    def score(
        self,
        memory: MemoryItem,
        now: datetime | None = None,
    ) -> float:
        ...


class ExponentialRecencyScorer(MemoryRecencyScorer):
    """
    Exponential time-decay based recency scorer.

    recency = exp(-lambda * age)

    where:

        age = age_in_days

    half_life_days controls how quickly the recency score decays.

    At exactly half_life_days:

        recency = 0.5
    """

    def __init__(
        self,
        half_life_days: float = 30.0,
    ) -> None:

        if half_life_days <= 0:
            raise ValueError(
                "half_life_days must be greater than 0"
            )

        self._half_life_days = half_life_days

    def score(
        self,
        memory: MemoryItem,
        now: datetime | None = None,
    ) -> float:

        if now is None:
            now = datetime.now(timezone.utc)

        created_at = memory.metadata.created_at

        if created_at.tzinfo is None:
            created_at = created_at.replace(
                tzinfo=timezone.utc
            )

        age_seconds = (
            now - created_at
        ).total_seconds()

        # Future timestamps should not produce a score
        # greater than 1.0.
        if age_seconds <= 0:
            return 1.0

        age_days = (
            age_seconds / 86400.0
        )

        decay_rate = (
            0.6931471805599453
            / self._half_life_days
        )

        score = exp(
            -decay_rate * age_days
        )

        return max(
            0.0,
            min(1.0, score),
        )