from typing import Protocol

from runtime.context.memory_item import MemoryItem
from runtime.memory.memory_candidate_retriever import MemoryCandidateRetriever, KeywordMemoryCandidateRetriever
from runtime.memory.memory_ranker import MemoryRanker, ImportanceMemoryRanker


class MemoryRetriever(Protocol):
    """
    High-level Memory retrieval strategy.

    Coordinates candidate retrieval, ranking and result limiting.
    """

    def retrieve(
        self,
        memories: list[MemoryItem],
        query: str,
        limit: int = 10,
    ) -> list[MemoryItem]:
        ...


class DefaultMemoryRetriever(MemoryRetriever):
    """
    Default Memory retrieval pipeline.

    Pipeline:

        candidate retrieval
            ↓
        ranking
            ↓
        limit
    """
    def __init__(
            self,
            candidate_retriever: MemoryCandidateRetriever | None = None,
            ranker: MemoryRanker | None = None,
    ) -> None:
        self._candidate_retriever = candidate_retriever or KeywordMemoryCandidateRetriever()

        self._ranker = ranker or ImportanceMemoryRanker()

    def retrieve(
        self,
        memories: list[MemoryItem],
        query: str,
        limit: int = 10,
    ) -> list[MemoryItem]:

        if limit <= 0:
            return []

        candidates = self._candidate_retriever.retrieve(memories, query)

        ranked = self._ranker.rank(candidates, query)

        return ranked[:limit]