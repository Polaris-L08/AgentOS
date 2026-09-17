from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        now = created_at or datetime.now(timezone.utc)

        self._state = ExecutionState(
            execution_id=execution_id,
            status=ExecutionStatus.CREATED,
            task_id=task_id,
            session_id=session_id,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )

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
            metadata=state.metadata,
            created_at=state.created_at,
        )

        execution._state = state.model_copy(deep=True)

        return execution

    @property
    def execution_id(self) -> str:
        """
        Return the logical Execution identity.
        """
        return self._state.execution_id

    @property
    def status(self) -> ExecutionStatus:
        """
        Return the current lifecycle status.
        """
        return self._state.status

    @property
    def task_id(self) -> str | None:
        """
        Return the associated task identifier.
        """
        return self._state.task_id

    @property
    def session_id(self) -> str | None:
        """
        Return the associated session identifier.
        """
        return self._state.session_id

    @property
    def current_checkpoint_id(self) -> str | None:
        """
        Return the identifier of the current recovery checkpoint.
        """
        return self._state.current_checkpoint_id

    @property
    def metadata(self) -> dict[str, Any]:
        """
        Return Execution metadata.

        A copy is returned so callers cannot mutate the internal
        logical state without going through the Execution object.
        """
        return dict(self._state.metadata)

    def set_checkpoint(self, checkpoint_id: str | None) -> None:
        """
        Set the current recovery checkpoint.

        The checkpoint identifier is a logical reference only.
        Execution does not load, persist, or otherwise manage the
        Checkpoint object itself.
        """
        self._state = self._state.model_copy(
            update={
                "current_checkpoint_id": checkpoint_id,
                "updated_at": datetime.now(timezone.utc),
            }
        )

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

        The returned state is detached from the live Execution object.
        """
        return self._state.model_copy(deep=True)

    def _transition(
        self,
        *,
        expected: ExecutionStatus,
        target: ExecutionStatus,
    ) -> None:
        current = self._state.status

        if current != expected:
            raise ExecutionLifecycleError(
                f"Invalid Execution lifecycle transition: "
                f"{current} -> {target}. "
                f"Expected current status: {expected}."
            )

        self._state = self._state.model_copy(
            update={
                "status": target,
                "updated_at": datetime.now(timezone.utc),
            }
        )