from typing import Protocol

from runtime.context.memory_item import MemoryItem


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


class ImportanceMemoryRanker:
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