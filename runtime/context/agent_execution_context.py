from dataclasses import dataclass

from agents.identity import AgentIdentity
from runtime.checkpoint.checkpoint import AgentCheckpoint
from runtime.context.context_state import ContextState
from runtime.context.runtime_context import RuntimeContext
from runtime.loop.loop_state import LoopState


@dataclass(slots=True)
class AgentExecutionContext:
    """
    Context for a single Agent execution.

    Lifecycle:

        AgentInstance
              |
              |
        AgentExecutionContext
              |
              |
        Agent execution

    It owns:
        - Agent private execution state
        - Loop state

    It references:
        - RuntimeContext

    RuntimeContext is shared between agents.
    AgentExecutionContext is isolated.
    """

    runtime_context: RuntimeContext

    agent_identity: AgentIdentity

    state: ContextState

    loop: LoopState

    @classmethod
    def create(cls, runtime_context: RuntimeContext, agent_identity: AgentIdentity) -> "AgentExecutionContext":
        """
        Create isolated execution context.
        for one Agent invocation.
        """

        return cls(runtime_context, agent_identity, ContextState(), LoopState())

    def create_checkpoint(self) -> AgentCheckpoint:

        return AgentCheckpoint(
            agent_id=self.agent_identity.agent_id,
            state=self.state,
            loop=self.loop,
        )