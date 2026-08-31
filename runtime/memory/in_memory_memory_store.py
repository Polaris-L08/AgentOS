from __future__ import annotations

from datetime import datetime, timezone

from runtime.context.memory_item import MemoryItem
from runtime.memory.memory_query import MemoryQuery
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

    async def query(
            self,
            scope: MemoryScope,
            query: MemoryQuery,
    ) -> list[MemoryItem]:
        memories = self._memories.get(scope, [])

        result: list[MemoryItem] = []

        for item in memories:
            if (
                query.source is not None
                and item.source != query.source
            ):
                continue

            if (
                query.min_importance is not None
                and item.importance < query.min_importance
            ):
                continue

            created_at = item.metadata.created_at

            if (
                query.created_after is not None
                and created_at <= query.created_after
            ):
                continue

            if (
                query.created_before is not None
                and created_at >= query.created_before
            ):
                continue

            if (
                not query.include_expired
                and item.is_expired()
            ):
                continue

            result.append(item)

            if (
                query.limit is not None
                and len(result) >= query.limit
            ):
                break

        return result