from datetime import datetime, timezone
from typing import Protocol

from runtime.context.memory_item import MemoryItem
from runtime.memory.memory_recency import MemoryRecencyScorer, ExponentialRecencyScorer


class MemoryRanker(Protocol):
    """
    Strategy for ranking retrieved Memory candidates.
    """

    def rank(
        self,
        memories: list[MemoryItem],
        query: str,
    ) -> list[MemoryItem]:
        ...


class ImportanceMemoryRanker(MemoryRanker):
    """
    Rank Memory items by their importance.

    Higher importance comes first.

    The implementation deliberately does not know about:

    - MemoryStore
    - MemoryRuntime
    - MemoryScope
    - RuntimeContext
    - MemoryRetriever
    """

    def rank(
        self,
        memories: list[MemoryItem],
        query: str,
    ) -> list[MemoryItem]:

        return sorted(
            memories,
            key=lambda item: item.importance,
            reverse=True,
        )

class ImportanceRecencyMemoryRanker(MemoryRanker):
    """
    Rank Memory items using both importance and recency.

    final_score =
        importance_weight * importance
        +
        recency_weight * recency

    Both importance and recency are normalized to [0.0, 1.0].
    """

    def __init__(
        self,
        recency_scorer: MemoryRecencyScorer | None = None,
        importance_weight: float = 0.5,
        recency_weight: float = 0.5,
    ) -> None:

        if importance_weight < 0:
            raise ValueError(
                "importance_weight must be >= 0"
            )

        if recency_weight < 0:
            raise ValueError(
                "recency_weight must be >= 0"
            )

        if (
            importance_weight == 0
            and recency_weight == 0
        ):
            raise ValueError(
                "At least one ranking weight must be greater than 0"
            )

        self._recency_scorer = (
            recency_scorer
            or ExponentialRecencyScorer()
        )

        self._importance_weight = (
            importance_weight
        )

        self._recency_weight = (
            recency_weight
        )

        total_weight = (
            importance_weight
            + recency_weight
        )

        self._importance_weight /= total_weight
        self._recency_weight /= total_weight

    def rank(
        self,
        memories: list[MemoryItem],
        query: str,
    ) -> list[MemoryItem]:

        now = datetime.now(timezone.utc)

        scored = [
            (
                item,
                self._calculate_score(
                    item,
                    now,
                ),
            )
            for item in memories
        ]

        scored.sort(
            key=lambda pair: pair[1],
            reverse=True,
        )

        return [
            item
            for item, _ in scored
        ]

    def _calculate_score(
        self,
        memory: MemoryItem,
        now: datetime,
    ) -> float:

        recency = self._recency_scorer.score(
            memory,
            now=now,
        )

        return (
            self._importance_weight
            * memory.importance
            +
            self._recency_weight
            * recency
        )