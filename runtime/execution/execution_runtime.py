from dataclasses import dataclass
from datetime import datetime, timezone

from runtime.context.runtime_context import RuntimeContext
from runtime.loop.loop_state import LoopState
from runtime.tracing.trace import Trace
from runtime.tracing.trace_context import TraceContext
from runtime.tracing.trace_recorder import TraceRecorder


@dataclass(slots=True)
class ExecutionRuntime:

    trace_recorder: TraceRecorder

    def create_context(self) -> RuntimeContext:
        """
        Create RuntimeContext.

        Runtime owns:

        - trace
        - shared execution space

        Agent state is created later by AgentExecutionContext.
        """

        trace = Trace(trace_id=self._create_id(), start_time=datetime.now(timezone.utc))

        trace_context = TraceContext(recorder=self.trace_recorder, trace=trace)

        trace_context.start_span(name="agent.run", metadata={"type": "root"})

        return RuntimeContext(trace=trace_context)

    async def close(self, runtime_context: RuntimeContext):
        """
        Finish execution trace.
        """
        runtime_context.trace.end_span()

        runtime_context.trace.trace.end_time = datetime.now(timezone.utc)

    def _create_id(self):
        import uuid
        return str(uuid.uuid4())