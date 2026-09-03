from dataclasses import dataclass
from typing import TYPE_CHECKING

from agents.identity import AgentIdentity
from runtime.checkpoint.checkpoint import AgentCheckpoint
from runtime.context.agent_context import AgentContext
from runtime.context.context_state import ContextState
from runtime.context.runtime_context import RuntimeContext
from runtime.loop.loop_state import LoopState

if TYPE_CHECKING:
    from agents.base_agent import BaseAgent
    from runtime.memory.memory_runtime import MemoryRuntime


@dataclass(slots=True)
class AgentExecutionContext:
    """
    Context for a single Agent execution.

    Lifecycle:

        Agent
          |
          +---- AgentContext
          |        |
          |        +---- survives multiple executions
          |
          +---- AgentExecutionContext
                   |
                   +---- one invocation
                   |
                   +---- execution-local state
                   +---- MemoryRuntime reference

    RuntimeContext is shared by all Agents participating
    in the same Runtime execution.

    AgentContext and MemoryRuntime belong to the Agent instance.
    AgentExecutionContext provides access to them for one invocation
    without copying or owning their long-lived state.

    Memory itself is NOT stored inside AgentExecutionContext.
    The ``memory`` field is only a reference to the Agent-owned
    MemoryRuntime.
    """

    runtime_context: RuntimeContext

    agent_identity: AgentIdentity

    agent_context: AgentContext

    memory: "MemoryRuntime"

    # Deprecated
    state: ContextState

    loop: LoopState

    @classmethod
    def create(
            cls,
            runtime_context: RuntimeContext,
            agent: "BaseAgent",
    ) -> "AgentExecutionContext":
        """
        Create isolated execution context for one Agent invocation.
        """

        return cls(runtime_context, agent.identity, agent.context, agent.memory, ContextState(), LoopState())

    @classmethod
    def restore(cls, runtime_context: RuntimeContext, agent: "BaseAgent",
                checkpoint: AgentCheckpoint) -> "AgentExecutionContext":
        """
        Restore execution-local state from checkpoint.

        The AgentContext is obtained from the live Agent instance
        rather than restored from the checkpoint.
        """

        return cls(runtime_context, agent.identity, agent.context, agent.memory, checkpoint.state, checkpoint.loop)
