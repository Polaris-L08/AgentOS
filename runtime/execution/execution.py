from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from runtime.execution.execution_state import (
    ExecutionState,
    ExecutionStatus,
)


class ExecutionLifecycleError(RuntimeError):
    """
    Raised when an invalid Execution lifecycle transition is requested.
    """


class Execution:
    """
    Logical Execution.

    Execution represents one logical User Request execution.

    It is intentionally independent of:

    - ExecutionRuntime
    - ExecutionHandle
    - RuntimeContext
    - Persistence backend

    Execution owns the logical lifecycle of an execution.

    The live Runtime that executes this logical Execution is managed
    separately by ExecutionRuntime / ExecutionHandle.
    """

    def __init__(
        self,
        *,
        execution_id: str,
        task_id: str | None = None,
        session_id: str | None = None,
        current_checkpoint_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        status: ExecutionStatus = ExecutionStatus.CREATED,
        updated_at: datetime | None = None,
    ) -> None:
        now = created_at or datetime.now(timezone.utc)

        self._execution_id = execution_id
        self._task_id = task_id
        self._session_id = session_id
        self._current_checkpoint_id = current_checkpoint_id
        self._status = status
        self._metadata = dict(metadata or {})
        self._created_at = now
        self._updated_at = updated_at or now

    @classmethod
    def from_state(
        cls,
        state: ExecutionState,
    ) -> Execution:
        """
        Reconstruct a logical Execution from durable state.

        This method reconstructs only the logical Execution object.
        It does not create an ExecutionRuntime, ExecutionHandle, or
        RuntimeContext.
        """
        execution = cls(
            execution_id=state.execution_id,
            task_id=state.task_id,
            session_id=state.session_id,
            current_checkpoint_id=state.current_checkpoint_id,
            metadata=state.metadata,
            created_at=state.created_at,
            status=state.status,
            updated_at=state.updated_at,
        )

        return execution

    @property
    def execution_id(self) -> str:
        """
        Return the logical Execution identity.
        """
        return self._execution_id

    @property
    def status(self) -> ExecutionStatus:
        """
        Return the current lifecycle status.
        """
        return self._status

    @property
    def task_id(self) -> str | None:
        """
        Return the associated task identifier.
        """
        return self._task_id

    @property
    def session_id(self) -> str | None:
        """
        Return the associated session identifier.
        """
        return self._session_id

    @property
    def current_checkpoint_id(self) -> str | None:
        """
        Return the identifier of the current recovery checkpoint.
        """
        return self._current_checkpoint_id

    @property
    def metadata(self) -> dict[str, Any]:
        """
        Return Execution metadata.

        A copy is returned so callers cannot mutate the internal
        logical state without going through the Execution object.
        """
        return dict(self._metadata)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def is_terminal(self) -> bool:
        """
        Return whether the Execution has reached a terminal state.
        """
        return self.status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        }

    def set_checkpoint(self, checkpoint_id: str | None) -> None:
        """
        Set the current recovery checkpoint.

        Execution stores only the checkpoint identifier. It does not
        load, persist, or manage the Checkpoint object itself.
        """
        self._current_checkpoint_id = checkpoint_id
        self._updated_at = datetime.now(timezone.utc)

    def start(self) -> None:
        """
        Transition:

            CREATED -> RUNNING
        """
        self._transition(
            expected=ExecutionStatus.CREATED,
            target=ExecutionStatus.RUNNING,
        )

    def pause(self) -> None:
        """
        Transition:

            RUNNING -> PAUSED
        """
        self._transition(
            expected=ExecutionStatus.RUNNING,
            target=ExecutionStatus.PAUSED,
        )

    def resume(self) -> None:
        """
        Transition:

            PAUSED -> RUNNING
        """
        self._transition(
            expected=ExecutionStatus.PAUSED,
            target=ExecutionStatus.RUNNING,
        )

    def complete(self) -> None:
        """
        Transition:

            RUNNING -> COMPLETED
        """
        self._transition(
            expected=ExecutionStatus.RUNNING,
            target=ExecutionStatus.COMPLETED,
        )

    def fail(self) -> None:
        """
        Transition:

            RUNNING -> FAILED
        """
        self._transition(
            expected=ExecutionStatus.RUNNING,
            target=ExecutionStatus.FAILED,
        )

    def cancel(self) -> None:
        """
        Transition:

            RUNNING -> CANCELLED
        """
        self._transition(
            expected=ExecutionStatus.RUNNING,
            target=ExecutionStatus.CANCELLED,
        )

    def snapshot(self) -> ExecutionState:
        """
        Create a durable snapshot of the logical Execution.
        """
        return ExecutionState(
            execution_id=self._execution_id,
            status=self._status,
            task_id=self._task_id,
            session_id=self._session_id,
            current_checkpoint_id=self._current_checkpoint_id,
            created_at=self._created_at,
            updated_at=self._updated_at,
            metadata=dict(self._metadata),
        )

    def _transition(
        self,
        *,
        expected: ExecutionStatus,
        target: ExecutionStatus,
    ) -> None:
        current = self._status

        if current != expected:
            raise ExecutionLifecycleError(
                f"Invalid Execution lifecycle transition: "
                f"{current} -> {target}. "
                f"Expected current status: {expected}."
            )

        self._status = target
        self._updated_at = datetime.now(timezone.utc)