from __future__ import annotations

from runtime.context.memory_item import MemoryItem
from runtime.memory.memory_scope import MemoryScope
from runtime.memory.memory_store import MemoryStore


class InMemoryMemoryStore(MemoryStore):
    """
    In-process MemoryStore implementation.

    Memory is isolated by MemoryScope.
    """

    def __init__(self) -> None:
        self._memories: dict[MemoryScope, list[MemoryItem]] = {}

    async def write(
        self,
        scope: MemoryScope,
        item: MemoryItem,
    ) -> None:
        self._memories.setdefault(scope, []).append(item)

    async def read(
        self,
        scope: MemoryScope,
    ) -> list[MemoryItem]:
        return list(
            self._memories.get(scope, [])
        )

    async def forget(
        self,
        scope: MemoryScope,
        memory_id: str,
    ) -> None:

        memories = self._memories.get(scope)

        if memories is None:
            return

        self._memories[scope] = [
            item
            for item in memories
            if item.id != memory_id
        ]

    async def clear(
        self,
        scope: MemoryScope,
    ) -> None:

        self._memories.pop(
            scope,
            None,
        )