from __future__ import annotations

from abc import ABC, abstractmethod

from runtime.context.memory_item import MemoryItem
from runtime.memory.memory_scope import MemoryScope


class MemoryStore(ABC):
    """
    Storage boundary for Agent Memory.

    MemoryStore is responsible only for persistence and
    retrieval of raw Memory items belonging to a specific
    MemoryScope.

    Semantic retrieval is handled by MemoryRetriever.
    """

    @abstractmethod
    async def write(
        self,
        scope: MemoryScope,
        item: MemoryItem,
    ) -> None:
        """Persist one memory item for an Agent."""
        raise NotImplementedError

    @abstractmethod
    async def read(
        self,
        scope: MemoryScope,
    ) -> list[MemoryItem]:
        """Return all memory items belonging to an Agent."""
        raise NotImplementedError

    @abstractmethod
    async def forget(
        self,
        scope: MemoryScope,
        memory_id: str,
    ) -> None:
        """Delete one memory item belonging to an Agent."""
        raise NotImplementedError

    @abstractmethod
    async def clear(
        self,
        scope: MemoryScope,
    ) -> None:
        """Delete all memory items belonging to an Agent."""
        raise NotImplementedError