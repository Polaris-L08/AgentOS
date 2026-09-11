from __future__ import annotations

from copy import deepcopy

from runtime.execution.execution_state import ExecutionState
from runtime.persistence.execution_store import ExecutionStore


class InMemoryExecutionStore(ExecutionStore):
    """
    In-memory implementation of ExecutionStore.

    This implementation is intended for local execution, testing, and
    as a reference implementation of the ExecutionStore contract.

    It does not provide durability across process restarts.
    """

    def __init__(self) -> None:
        self._states: dict[str, ExecutionState] = {}

    async def save(self, state: ExecutionState) -> None:
        """
        Persist an ExecutionState in memory.

        Existing state with the same execution_id is replaced.
        """
        self._states[state.execution_id] = deepcopy(state)

    async def load(self, execution_id: str) -> ExecutionState | None:
        """
        Load an ExecutionState by execution_id.

        Returns None when the Execution does not exist.
        """
        state = self._states.get(execution_id)

        if state is None:
            return None

        return deepcopy(state)

    async def delete(self, execution_id: str) -> None:
        """
        Delete an ExecutionState by execution_id.

        Deleting a non-existent Execution is safe.
        """
        self._states.pop(execution_id, None)