from __future__ import annotations

from runtime.component import RuntimeComponent
from runtime.context import MemoryMetadata
from runtime.context.memory_item import MemoryItem, MemorySource
from runtime.context.runtime_context import RuntimeContext
from runtime.memory.memory_access_policy import MemoryAccessPolicy
from runtime.memory.memory_operation import MemoryOperation
from runtime.memory.memory_query import MemoryQuery
from runtime.memory.memory_retriever import MemoryRetriever, DefaultMemoryRetriever
from runtime.memory.memory_scope import MemoryScope
from runtime.memory.memory_scope_resolver import MemoryScopeResolver
from runtime.memory.memory_store import MemoryStore
from runtime.middleware.runtime_operation import RuntimeOperation


class MemoryRuntime(RuntimeComponent):
    """
    Runtime boundary for Agent Memory.

    Responsibilities:

    - Memory access control
    - Memory scope resolution
    - Candidate Memory loading
    - Memory retrieval
    - Runtime middleware integration
    - Memory mutation delegation

    MemoryRuntime does not implement persistence itself.

    Retrieval pipeline:

        MemoryQuery
            ↓
        MemoryStore.query()
            ↓
        Candidate Memories
            ↓
        MemoryRetriever
            ↓
        Candidate Retrieval
            ↓
        Ranking
            ↓
        Final Top-K
    """

    def __init__(
        self,
        scope_resolver: MemoryScopeResolver,
        store: MemoryStore,
        retriever: MemoryRetriever | None = None,
        access_policy: MemoryAccessPolicy | None = None,
        middleware_chain=None,
    ) -> None:

        super().__init__(middleware_chain)

        self._scope_resolver = scope_resolver
        self._store = store

        self._retriever = retriever or DefaultMemoryRetriever()

        self._access_policy = access_policy or MemoryAccessPolicy()

    # =========================================================
    # Scope Resolution
    # =========================================================
    def _resolve_scopes(self) -> list[MemoryScope]:
        """
        Resolve Memory scopes in priority order.
        """
        return self._scope_resolver.resolve()

    def _resolve_write_scope(self) -> MemoryScope:
        """
        Resolve the primary scope used for write operations.

        The first resolved scope has the highest priority and
        is therefore the primary write scope.
        """
        scopes = self._resolve_scopes()

        if not scopes:
            raise RuntimeError(
                "No memory scope is available for write."
            )

        return scopes[0]

    # =========================================================
    # Access Control
    # =========================================================

    def _check_access(
        self,
        operation: MemoryOperation,
    ) -> None:
        """
        Validate whether the requested Memory operation
        is allowed by the configured access policy.
        """
        if not self._access_policy.allows(operation):
            raise PermissionError(
                f"Memory operation "
                f"'{operation.value}' "
                f"is not allowed."
            )

    async def remember(
            self,
            content: str,
            runtime_context: RuntimeContext,
            *,
            importance: float = 1.0,
            source: MemorySource = MemorySource.HISTORY,
            metadata: MemoryMetadata | None = None,
    ) -> MemoryItem:
        """
        Create a MemoryItem and persist it through the normal write boundary.

        ``remember()`` is a convenience boundary for Agent-facing code.
        It does not perform persistence, scope resolution, or access control
        itself; those responsibilities remain in ``write()``.
        """
        item = MemoryItem(
            content=content,
            importance=importance,
            source=source,
            metadata=(
                metadata
                if metadata is not None
                else MemoryMetadata()
            ),
        )

        await self.write(
            item,
            runtime_context,
        )

        return item

    async def write(
        self,
        item: MemoryItem,
        runtime_context: RuntimeContext,
    ) -> None:
        """
        Write Memory to the primary Memory scope.
        Write operations never write to all resolved scopes.
        """
        self._check_access(MemoryOperation.WRITE)

        scope = self._resolve_write_scope()

        operation = RuntimeOperation(
            name="memory.write",
            component="memory_runtime",
            metadata={
                "scope_type": scope.type.value,
                "scope_id": scope.id,
            },
        )

        await self.invoke(
            operation,
            runtime_context,
            self._store.write,
            scope,
            item,
        )

    async def read(
        self,
        runtime_context: RuntimeContext,
    ) -> list[MemoryItem]:
        """
        Read Memory from all resolved scopes.

        Scope ordering is preserved.
        Higher-priority scopes are returned first.
        """
        self._check_access(MemoryOperation.READ)

        scopes = self._resolve_scopes()
        memories: list[MemoryItem] = []

        for scope in scopes:
            operation = RuntimeOperation(
                name="memory.read",
                component="memory_runtime",
                metadata={
                    "scope_type": scope.type.value,
                    "scope_id": scope.id,
                },
            )
            result = await self.invoke(
                operation,
                runtime_context,
                self._store.read,
                scope
            )

            memories.extend(result)

        return memories

    async def query(
        self,
        query: str,
        runtime_context: RuntimeContext,
        limit: int = 10,
        memory_query: MemoryQuery | None = None,
    ) -> list[MemoryItem]:
        """
        Retrieve Memory across all resolved scopes.

        The retrieval pipeline is:

            MemoryQuery
                ↓
            MemoryStore.query()
                ↓
            Candidate Memories
                ↓
            MemoryRetriever
                ↓
            Ranking
                ↓
            Final Top-K

        `memory_query` contains storage-level filtering
        constraints.

        `query` contains the retrieval text used by the
        MemoryRetriever.

        The final `limit` is applied by the MemoryRetriever
        after candidate retrieval and ranking.

        Scope ordering is preserved when candidate memories
        are collected from multiple scopes.
        """
        self._check_access(MemoryOperation.READ)

        if limit <= 0:
            return []

        scopes = self._resolve_scopes()
        memories: list[MemoryItem] = []

        # Each scope contributes a candidate pool.
        #
        # The final result limit is applied only after
        # candidates from all scopes have been combined
        # and passed through the Retrieval pipeline.
        candidate_limit = max(limit * 10, limit)
        store_query = memory_query
        if (
                store_query is not None
                and store_query.limit is not None
        ):
            store_query = store_query.model_copy(
                update={
                    'limit': candidate_limit
                }
            )

        if store_query is None:
            store_query = MemoryQuery()

        for scope in scopes:
            operation = RuntimeOperation(
                name="memory.query",
                component="memory_runtime",
                metadata={
                    "scope_type": scope.type.value,
                    "scope_id": scope.id,
                },
            )

            result = await self.invoke(
                operation,
                runtime_context,
                self._store.query,
                scope,
                store_query,
            )

            memories.extend(result)

        return self._retriever.retrieve(memories, query, limit)

    async def query_scope(
            self,
            scope: MemoryScope,
            query: str,
            runtime_context: RuntimeContext,
            limit: int = 10,
            memory_query: MemoryQuery | None = None,
    ) -> list[MemoryItem]:
        """
        Query Memory within one explicitly selected scope.

        The requested scope must belong to the set of scopes
        resolved by this MemoryRuntime.

        This keeps explicit single-scope retrieval inside the
        Runtime's existing scope boundary.

        ``memory_query`` is applied by MemoryStore.

        ``limit`` is the final Retrieval result limit and is
        applied by MemoryRetriever.
        """
        self._check_access(
            MemoryOperation.READ
        )

        if limit <= 0:
            return []

        scopes = self._resolve_scopes()

        if scope not in scopes:
            raise PermissionError(
                "The requested memory scope is not accessible "
                "through this MemoryRuntime."
            )

        store_query = (
            memory_query
            or MemoryQuery()
        )

        operation = RuntimeOperation(
            name="memory.query",
            component="memory_runtime",
            metadata={
                "scope_type": scope.type.value,
                "scope_id": scope.id,
            },
        )

        memories = await self.invoke(
            operation,
            runtime_context,
            self._store.query,
            scope,
            store_query,
        )

        return self._retriever.retrieve(
            memories,
            query,
            limit,
        )

    async def forget(
        self,
        memory_id: str,
        runtime_context: RuntimeContext,
    ) -> None:
        """
        Remove a Memory item from the first resolved scope
        containing the specified Memory ID.

        Scope priority is respected.
        """
        self._check_access(MemoryOperation.DELETE)

        scopes = self._resolve_scopes()

        for scope in scopes:
            read_operation = RuntimeOperation(
                name="memory.read",
                component="memory_runtime",
                metadata={
                    "scope_type": scope.type.value,
                    "scope_id": scope.id,
                },
            )
            memories = await self.invoke(
                read_operation,
                runtime_context,
                self._store.read,
                scope,
            )

            found = any(item.id == memory_id for item in memories)

            if not found:
                continue

            forget_operation = RuntimeOperation(
                name="memory.forget",
                component="memory_runtime",
                metadata={
                    "scope_type": scope.type.value,
                    "scope_id": scope.id,
                    "memory_id": memory_id,
                },
            )

            await self.invoke(
                forget_operation,
                runtime_context,
                self._store.forget,
                scope,
                memory_id,
            )

            return

    async def clear(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """
        Clear Memory from the primary Memory scope only.

        Shared scopes must never be cleared implicitly.
        """

        self._check_access(
            MemoryOperation.DELETE
        )

        scope = self._resolve_write_scope()

        operation = RuntimeOperation(
            name="memory.clear",
            component="memory_runtime",
            metadata={
                "scope_type": scope.type.value,
                "scope_id": scope.id,
            },
        )

        await self.invoke(
            operation,
            runtime_context,
            self._store.clear,
            scope,
        )