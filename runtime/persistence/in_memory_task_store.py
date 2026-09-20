from __future__ import annotations

from copy import deepcopy

from models.task_request import TaskRequest
from runtime.persistence.task_store import TaskStore


class InMemoryTaskStore(TaskStore):
    """
    In-memory implementation of TaskStore.

    This implementation is intended for:
        - local execution
        - testing
        - reference implementation of the TaskStore contract

    It does not provide durability across process restarts.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRequest] = {}

    async def save(
        self,
        task: TaskRequest,
    ) -> None:
        """
        Persist a TaskRequest in memory.

        Existing state with the same task_id is replaced.
        """
        self._tasks[task.task_id] = deepcopy(task)

    async def load(
        self,
        task_id: str,
    ) -> TaskRequest | None:
        """
        Load a TaskRequest by task_id.

        Returns None when the task does not exist.
        """
        task = self._tasks.get(task_id)

        if task is None:
            return None

        return deepcopy(task)

    async def delete(
        self,
        task_id: str,
    ) -> None:
        """
        Delete a TaskRequest.

        Deleting a non-existent task is safe.
        """
        self._tasks.pop(task_id, None)