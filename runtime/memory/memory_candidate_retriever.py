from typing import Protocol

from runtime.context.memory_item import MemoryItem


class MemoryCandidateRetriever(Protocol):
    """
    Strategy for retrieving candidate Memory items.

    A candidate retriever is responsible for recall,
    not final ranking.
    """

    def retrieve(
        self,
        memories: list[MemoryItem],
        query: str,
    ) -> list[MemoryItem]:
        ...


class KeywordMemoryCandidateRetriever(
    MemoryCandidateRetriever
):
    """
    Simple keyword-based candidate retrieval.

    This implementation performs recall only.
    It does not perform ranking or limit the final result set.
    """

    def retrieve(
        self,
        memories: list[MemoryItem],
        query: str,
    ) -> list[MemoryItem]:

        normalized_query = query.strip().lower()

        active_memories = [
            item
            for item in memories
            if not item.is_expired()
        ]

        if not normalized_query:
            return active_memories

        return [
            item
            for item in active_memories
            if normalized_query
            in item.content.lower()
        ]