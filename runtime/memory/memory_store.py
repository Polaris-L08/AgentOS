from __future__ import annotations

from abc import ABC, abstractmethod

from runtime.context.memory_item import MemoryItem


class MemoryStore(ABC):
    """
    Storage boundary for Agent Memory.

    MemoryStore is responsible only for storing and retrieving
    MemoryItem objects.

    It does not know about:

    - Agent reasoning
    - AgentExecutionContext
    - Workflow
    - Tool execution

    The agent_id argument establishes the storage isolation boundary.
    """

    @abstractmethod
    async def write(
        self,
        agent_id: str,
        item: MemoryItem,
    ) -> None:
        """Persist one memory item for an Agent."""
        raise NotImplementedError

    @abstractmethod
    async def read(
        self,
        agent_id: str,
    ) -> list[MemoryItem]:
        """Return all memory items belonging to an Agent."""
        raise NotImplementedError

    @abstractmethod
    async def query(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> list[MemoryItem]:
        """Return memory items matching a query."""
        raise NotImplementedError

    @abstractmethod
    async def forget(
        self,
        agent_id: str,
        memory_id: str,
    ) -> None:
        """Delete one memory item belonging to an Agent."""
        raise NotImplementedError

    @abstractmethod
    async def clear(
        self,
        agent_id: str,
    ) -> None:
        """Delete all memory items belonging to an Agent."""
        raise NotImplementedError