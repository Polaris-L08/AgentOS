from __future__ import annotations

from runtime.component import RuntimeComponent
from runtime.context.memory_item import MemoryItem
from runtime.context.runtime_context import RuntimeContext
from runtime.memory.memory_store import MemoryStore
from runtime.middleware.runtime_operation import RuntimeOperation


class MemoryRuntime(RuntimeComponent):
    """
    Runtime boundary for Agent Memory.

    Architecture:

        Agent
          |
          v
        MemoryRuntime
          |
          v
        MemoryStore

    MemoryRuntime owns the Agent-scoped identity used when
    accessing the Store.
    """

    def __init__(
        self,
        agent_id: str,
        store: MemoryStore,
        middleware_chain=None,
    ) -> None:

        super().__init__(middleware_chain)

        self.agent_id = agent_id
        self._store = store

    async def write(
        self,
        item: MemoryItem,
        runtime_context: RuntimeContext,
    ) -> None:

        operation = RuntimeOperation(
            name="memory.write",
            component="memory_runtime",
            metadata={
                "agent_id": self.agent_id,
            },
        )

        await self.invoke(
            operation,
            runtime_context,
            self._store.write,
            self.agent_id,
            item,
        )

    async def read(
        self,
        runtime_context: RuntimeContext,
    ) -> list[MemoryItem]:

        operation = RuntimeOperation(
            name="memory.read",
            component="memory_runtime",
            metadata={
                "agent_id": self.agent_id,
            },
        )

        return await self.invoke(
            operation,
            runtime_context,
            self._store.read,
            self.agent_id,
        )

    async def query(
        self,
        query: str,
        runtime_context: RuntimeContext,
        limit: int = 10,
    ) -> list[MemoryItem]:

        operation = RuntimeOperation(
            name="memory.query",
            component="memory_runtime",
            metadata={
                "agent_id": self.agent_id,
                "limit": limit,
            },
        )

        return await self.invoke(
            operation,
            runtime_context,
            self._store.query,
            self.agent_id,
            query,
            limit,
        )

    async def forget(
        self,
        memory_id: str,
        runtime_context: RuntimeContext,
    ) -> None:

        operation = RuntimeOperation(
            name="memory.forget",
            component="memory_runtime",
            metadata={
                "agent_id": self.agent_id,
                "memory_id": memory_id,
            },
        )

        await self.invoke(
            operation,
            runtime_context,
            self._store.forget,
            self.agent_id,
            memory_id,
        )

    async def clear(
        self,
        runtime_context: RuntimeContext,
    ) -> None:

        operation = RuntimeOperation(
            name="memory.clear",
            component="memory_runtime",
            metadata={
                "agent_id": self.agent_id,
            },
        )

        await self.invoke(
            operation,
            runtime_context,
            self._store.clear,
            self.agent_id,
        )