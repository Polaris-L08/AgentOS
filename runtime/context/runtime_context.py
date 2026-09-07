from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from runtime.context.shared_context import SharedContext
from runtime.tracing.trace_context import TraceContext


@dataclass(slots=True, frozen=True)
class RuntimeContext:
    """
    Runtime level execution context.

    Lifecycle:
        one user request
        one workflow execution

    Shared by all Agents participating in the same execution.

    It does NOT own Agent private state.

    Agent private state belongs to:
        AgentExecutionContext

    RuntimeContext is a live execution object.
    It is reconstructed from durable execution state during recovery;
    it is not itself the durable checkpoint representation.
    """

    trace: TraceContext

    shared_context: SharedContext = field(default_factory=SharedContext)

    runtime_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def create(
            cls,
            trace: TraceContext,
            *,
            runtime_id: str | None = None,
            shared_context: SharedContext | None = None,
    ) -> RuntimeContext:
        return cls(
            trace=trace,
            shared_context=(
                shared_context
                if shared_context is not None
                else SharedContext()
            ),
            runtime_id=(
                runtime_id
                if runtime_id is not None
                else str(uuid.uuid4())
            ),
        )