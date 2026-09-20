from typing import Protocol

from models.task_request import TaskRequest


class TaskStore(Protocol):
    """
    Persistence contract for TaskRequest.

    TaskStore persists the durable input of a logical Execution.

    TaskStore does not own:
        - Execution lifecycle
        - RuntimeContext
        - ExecutionHandle
        - Agent execution
        - Checkpoint state
    """

    async def save(
        self,
        task: TaskRequest,
    ) -> None:
        """
        Persist a TaskRequest.

        An existing task with the same task_id is replaced.
        """
        ...

    async def load(
        self,
        task_id: str,
    ) -> TaskRequest | None:
        """
        Load a TaskRequest by task_id.

        Returns None when the task does not exist.
        """
        ...

    async def delete(
        self,
        task_id: str,
    ) -> None:
        """
        Delete a TaskRequest.

        Deleting a non-existent task is safe.
        """
        ...