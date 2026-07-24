from __future__ import annotations

import uuid
from copy import deepcopy
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

    state: ContextState

    trace: TraceContext

    loop: LoopState

    runtime_id: str = str(uuid.uuid4())

    def fork(self) -> "RuntimeContext":
        """
        Create child Agent execution context.

        Isolation rules:

        Shared:
            TraceContext

        Copy:
            ContextState
            LoopState

        Reason:

            Multiple Agents share
            execution trace,

            but they have independent
            reasoning state and loop state.
        """
        return RuntimeContext(
            runtime_id=self.runtime_id,
            state=deepcopy(self.state),
            trace=self.trace,
            loop=self.loop.copy()
        )