from __future__ import annotations

import uuid
from copy import deepcopy
from dataclasses import dataclass, field

from runtime.context.context_state import ContextState
from runtime.context.shared_context import SharedContext
from runtime.loop.loop_state import LoopState
from runtime.tracing.trace_context import TraceContext


@dataclass(slots=True, frozen=True)
class RuntimeContext:
    """
    Runtime level execution context.

    Lifecycle:

        one user request
        one workflow execution


    Shared by all Agents participating
    in the same execution.

    It does NOT own Agent private state.

    Agent private state belongs to:

        AgentExecutionContext
    """

    trace: TraceContext

    shared_context: SharedContext = field(default_factory=SharedContext)

    runtime_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # -------------------------------------------------
    # Migration compatibility fields
    #
    # Deprecated:
    # These fields will be removed after
    # AgentExecutionContext migration finishes.
    # -------------------------------------------------

    state: ContextState | None = None

    loop: LoopState | None = None
