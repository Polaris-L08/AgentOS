from abc import ABC, abstractmethod

from agents.identity import AgentIdentity
from runtime.component import RuntimeComponent
from runtime.context import AgentExecutionContext
from runtime.context.agent_context import AgentContext
from runtime.memory.in_memory_memory_store import InMemoryMemoryStore
from runtime.memory.memory_access_policy import MemoryAccessPolicy
from runtime.memory.memory_runtime import MemoryRuntime
from runtime.memory.memory_scope import MemoryScope, MemoryScopeType
from runtime.memory.memory_store import MemoryStore
from .agent_result import AgentResult


class BaseAgent(RuntimeComponent, ABC):
    def __init__(
            self,
            identity: AgentIdentity,
            middleware_chain = None,
            memory_store: MemoryStore | None = None,
            memory_access_policy: MemoryAccessPolicy | None = None,
    ):
        super().__init__(middleware_chain)
        self.identity = identity
        # AgentContext belongs to the Agent instance.
        #
        # It is intentionally created here instead of inside
        # AgentExecutionContext.create().
        #
        # Therefore the context survives across multiple
        # Agent invocations.
        self.context = AgentContext()

        # Memory is an Agent capability with a separate runtime and
        # storage boundary. The default store is intentionally in-memory
        # for the current Phase11 implementation.
        self.memory = MemoryRuntime(
            scope=MemoryScope(
                type=MemoryScopeType.AGENT,
                id=identity.agent_id,
            ),
            store=memory_store or InMemoryMemoryStore(),
            access_policy=memory_access_policy,
        )

    async def execute(self, task, agent_execution_context: AgentExecutionContext):
        """
        Unified agent execution entry.

        AgentRuntime creates the execution context and passes
        the Agent's long-lived AgentContext into it.

        Runtime responsibilities:
            - invocation
            - middleware
            - tracing
            - checkpoint
            - execution lifecycle

        Agent responsibilities:
            - reasoning
            - planning
            - decision
        """
        result = await self.run(task, agent_execution_context)
        if isinstance(result, AgentResult):
            return result

        return AgentResult(success=True, output=result)

    @abstractmethod
    async def run(
            self,
            task,
            agent_execution_context: AgentExecutionContext
    ) -> AgentResult:
        """
        Agent execution entry.

        Agent decides:
        - planning
        - action generation
        - reflection

        Runtime handles:
        - middleware
        - tracing
        - checkpoint
        """
        pass