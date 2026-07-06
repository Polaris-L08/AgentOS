from __future__ import annotations

from dataclasses import dataclass

from runtime.context.context_state import ContextState
from runtime.loop.loop_state import LoopState
from runtime.tracing.trace_context import TraceContext


@dataclass(slots=True, frozen=True)
class RuntimeContext:
    """
    Unified runtime execution context.

    This is the ONLY object passed into Middleware layer.
    It aggregates all orthogonal runtime concerns:
    - semantic agent state
    - tracing state
    - loop control state
    """

    context: ContextState

    trace: TraceContext

    loop: LoopState

    def fork(self) -> "RuntimeContext":
        """
        Create a shallow copy for isolated execution scopes.
        """
        return RuntimeContext(
            context=self.context,
            trace=self.trace,
            loop=self.loop
        )