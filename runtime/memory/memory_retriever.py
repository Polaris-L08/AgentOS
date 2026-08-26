from typing import Protocol

from runtime.context.memory_item import MemoryItem


class MemoryRetriever(Protocol):
    """
    Strategy for retrieving relevant Memory items from
    a collection of candidate Memory items.

    A MemoryRetriever does not know about:

    - MemoryStore
    - MemoryRuntime
    - MemoryScope
    - Agent
    - RuntimeContext
    """

    def retrieve(
        self,
        memories: list[MemoryItem],
        query: str,
        limit: int = 10,
    ) -> list[MemoryItem]:
        ...


class KeywordMemoryRetriever:
    """
    Simple keyword-based Memory retrieval strategy.

    The implementation is intentionally simple.

    It performs case-insensitive substring matching against
    MemoryItem.content.

    This implementation exists to establish the Retrieval
    boundary. It is not intended to be the final retrieval
    implementation.
    """

    def retrieve(
        self,
        memories: list[MemoryItem],
        query: str,
        limit: int = 10,
    ) -> list[MemoryItem]:

        if limit <= 0:
            return []

        active_memories = [
            item
            for item in memories
            if not item.is_expired()
        ]

        normalized_query = query.strip().lower()

        if not normalized_query:
            return active_memories[:limit]

        matches = [
            item
            for item in active_memories
            if normalized_query in item.content.lower()
        ]

        return matches[:limit]