from __future__ import annotations

from runtime.component import RuntimeComponent
from runtime.context.memory_item import MemoryItem
from runtime.context.runtime_context import RuntimeContext
from runtime.memory.memory_access_policy import MemoryAccessPolicy
from runtime.memory.memory_operation import MemoryOperation
from runtime.memory.memory_store import MemoryStore
from runtime.middleware.runtime_operation import RuntimeOperation


class MemoryRuntime(RuntimeComponent):
    """
    Runtime boundary for Agent Memory.

    MemoryRuntime separates Agent-facing memory operations from the
    concrete storage implementation.

    Architecture:

        Agent
          |
          v
        MemoryRuntime
          |
          v
        MemoryStore

    MemoryRuntime owns the Agent-scoped identity used when accessing
    the Store. Agents therefore do not need to pass agent_id on every
    memory operation and do not need to know which Store is used.
    """

    def __init__(
        self,
        agent_id: str,
        store: MemoryStore,
        access_policy: MemoryAccessPolicy | None = None,
        middleware_chain=None,
    ) -> None:

        super().__init__(middleware_chain)

        self.agent_id = agent_id
        self._store = store
        self._access_policy = access_policy or MemoryAccessPolicy()

    def _check_access(self, operation: MemoryOperation) -> None:
        if not self._access_policy.allows(operation):
            raise PermissionError(
                f"Memory operation '{operation.value}' is not allowed "
                f"for agent '{self.agent_id}'."
            )

    async def write(
        self,
        item: MemoryItem,
        runtime_context: RuntimeContext,
    ) -> None:
        self._check_access(MemoryOperation.WRITE)

        operation = RuntimeOperation(
            name="memory.write",
            component="memory_runtime",
            metadata={"agent_id": self.agent_id},
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
        self._check_access(MemoryOperation.READ)

        operation = RuntimeOperation(
            name="memory.read",
            component="memory_runtime",
            metadata={"agent_id": self.agent_id},
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
        self._check_access(MemoryOperation.READ)

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
        self._check_access(MemoryOperation.DELETE)

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
        self._check_access(MemoryOperation.DELETE)

        operation = RuntimeOperation(
            name="memory.clear",
            component="memory_runtime",
            metadata={"agent_id": self.agent_id},
        )

        await self.invoke(
            operation,
            runtime_context,
            self._store.clear,
            self.agent_id,
        )