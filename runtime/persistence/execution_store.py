from __future__ import annotations

from typing import Protocol

from runtime.execution.execution_state import ExecutionState


class ExecutionStore(Protocol):
    """
    Persistence contract for durable Execution state.

    Implementations may use an in-memory store, PostgreSQL, or another
    durable storage backend.
    """

    async def save(self, state: ExecutionState) -> None:
        """
        Persist an ExecutionState.

        If an Execution with the same execution_id already exists, the
        implementation should replace its durable state.
        """
        ...

    async def load(self, execution_id: str) -> ExecutionState | None:
        """
        Load an ExecutionState by execution_id.

        Returns None when the Execution does not exist.
        """
        ...

    async def delete(self, execution_id: str) -> None:
        """
        Delete an ExecutionState by execution_id.

        Deleting a non-existent Execution should be safe.
        """
        ...