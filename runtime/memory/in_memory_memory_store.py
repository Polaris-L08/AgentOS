from __future__ import annotations

from runtime.context.memory_item import MemoryItem
from runtime.memory.memory_store import MemoryStore


class InMemoryMemoryStore(MemoryStore):
    """
    In-process MemoryStore implementation.

    This implementation is intentionally simple and is used
    to establish Memory semantics before introducing external
    persistence.
    """

    def __init__(self) -> None:
        self._memories: dict[str, list[MemoryItem]] = {}

    async def write(
        self,
        agent_id: str,
        item: MemoryItem,
    ) -> None:
        self._memories.setdefault(agent_id, []).append(item)

    async def read(
        self,
        agent_id: str,
    ) -> list[MemoryItem]:
        return list(
            self._memories.get(agent_id, [])
        )

    async def query(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> list[MemoryItem]:

        if limit <= 0:
            return []

        normalized_query = query.strip().lower()

        if not normalized_query:
            return (
                await self.read(agent_id)
            )[:limit]

        matches = [
            item
            for item in self._memories.get(
                agent_id,
                [],
            )
            if normalized_query in item.content.lower()
        ]

        return matches[:limit]

    async def forget(
        self,
        agent_id: str,
        memory_id: str,
    ) -> None:

        memories = self._memories.get(agent_id)

        if memories is None:
            return

        self._memories[agent_id] = [
            item
            for item in memories
            if item.id != memory_id
        ]

    async def clear(
        self,
        agent_id: str,
    ) -> None:

        self._memories.pop(
            agent_id,
            None,
        )