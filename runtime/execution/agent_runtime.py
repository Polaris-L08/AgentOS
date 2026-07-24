from __future__ import annotations

from agents import BaseAgent, AgentResult
from models.task_request import TaskRequest
from runtime.component import RuntimeComponent
from runtime.context import AgentExecutionContext
from runtime.context.runtime_context import RuntimeContext
from runtime.events.event import Event
from runtime.events.publisher import EventPublisher
from runtime.middleware.runtime_operation import RuntimeOperation


class AgentRuntime(RuntimeComponent):
    """
    Runtime responsible for Agent invocation.

    It provides:

        Agent A
            |
            |
        AgentRuntime
            |
            |
        Agent B


    It does NOT manage:

        - Agent registry
        - Agent lifecycle
        - Agent discovery

    It only executes an Agent.
    """

    def __init__(self, publisher: EventPublisher | None = None, middleware_chain =None):
        super().__init__(middleware_chain)
        self._publisher = publisher

    async def execute(self, agent: BaseAgent, task: TaskRequest, runtime_context: RuntimeContext) -> AgentResult:
        """
        Execute another Agent.

        Example:

            supervisor.execute(
                research_agent,
                task,
                context
            )

        """

        operation = RuntimeOperation(
            name="agent.execute",
            component="agent_runtime",
            metadata={
                "agent_id": agent.identity.agent_id,
                "agent_type": agent.identity.agent_type,
                "agent_name": agent.identity.name,
            }
        )

        # create isolated Agent execution context
        agent_execution_context = AgentExecutionContext.create(runtime_context, agent.identity)

        await self._publish(
            Event(
                type="agent.started",
                source="agent_runtime",
                payload={
                    "agent_id": agent.identity.agent_id,
                    "agent_type": agent.identity.agent_type,
                    "agent_name": agent.identity.name,
                },
                trace_id=runtime_context.trace.trace.trace_id,
                sender=None,
                receiver=agent.identity.name,
                correlation_id=runtime_context.runtime_id
            )
        )

        # async def invoke_agent() -> AgentResult:
        #     return await agent.execute(task, child_context)

        # return await self.invoke(
        #     operation,
        #     child_context,
        #     invoke_agent
        # )
        try:
            result = await self.invoke(
                operation,
                runtime_context,
                agent.execute,
                task,
                agent_execution_context
            )

            await self._publish(
                Event(
                    type="agent.completed",
                    source="agent_runtime",
                    payload={
                        "agent_id": agent.identity.agent_id,
                        "success": result.success
                    },
                    trace_id=runtime_context.trace.trace.trace_id,
                    receiver=agent.identity.name,
                    correlation_id=runtime_context.runtime_id
                )
            )

            return result
        except Exception as e:

            await self._publish(
                Event(
                    type="agent.failed",
                    source="agent_runtime",
                    payload={
                        "agent_id": agent.identity.agent_id,
                        "error": str(e),
                    },
                    trace_id=runtime_context.trace.trace.trace_id,
                    receiver=agent.identity.name,
                    correlation_id=runtime_context.runtime_id
                )
            )

    async def _publish(self, event: Event):
        if self._publisher is None:
            return

        self._publisher.emit(event)