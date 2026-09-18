from __future__ import annotations

from typing import TYPE_CHECKING

from runtime.context.runtime_context import RuntimeContext
from runtime.execution import Execution

if TYPE_CHECKING:
    from runtime.execution.execution_runtime import ExecutionRuntime


class ExecutionHandle:
    """
    Lifecycle handle for one Execution.

    An ExecutionHandle represents one concrete execution and provides
    controlled access to its RuntimeContext and lifecycle.

    Relationship:

        ExecutionRuntime
                |
                | creates
                v
        ExecutionHandle
                |
                v
        RuntimeContext
    """

    def __init__(
        self,
        runtime: ExecutionRuntime,
        execution: Execution,
        runtime_context: RuntimeContext,
    ) -> None:
        self._runtime = runtime
        self._execution = execution
        self._runtime_context = runtime_context
        self._closed = False

    @property
    def execution(self) -> Execution:
        """
        Return the logical Execution associated with this handle.
        """
        return self._execution

    @property
    def runtime_context(self) -> RuntimeContext:
        """
        Return the RuntimeContext belonging to this Execution.
        """
        return self._runtime_context

    @property
    def execution_id(self) -> str:
        """
        Return the unique identifier of this Execution.
        """
        return self._execution.execution_id

    @property
    def runtime_id(self) -> str:
        """
        Return the live RuntimeContext identity.
        """
        return self._runtime_context.runtime_id

    @property
    def closed(self) -> bool:
        """
        Return whether this Execution has been closed.
        """
        return self._closed

    async def close(self) -> None:
        """
        Close this Execution.

        Closing is idempotent. Calling close() more than once does not
        close the underlying RuntimeContext again.
        """
        if self._closed:
            return

        await self._runtime.close(
            self._runtime_context
        )

        self._closed = True

    async def __aenter__(self) -> ExecutionHandle:
        """
        Enter the asynchronous Execution context.
        """
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """
        Close the Execution when leaving the async context.
        """
        await self.close()