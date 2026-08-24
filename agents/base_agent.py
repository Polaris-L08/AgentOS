from abc import ABC, abstractmethod

from agents.identity import AgentIdentity
from runtime.component import RuntimeComponent
from runtime.context import AgentExecutionContext
from runtime.context.agent_context import AgentContext
from .agent_result import AgentResult


class BaseAgent(RuntimeComponent, ABC):
    def __init__(self, identity: AgentIdentity, middleware_chain = None):
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