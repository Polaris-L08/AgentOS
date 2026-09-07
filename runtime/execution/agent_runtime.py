from __future__ import annotations

from agents import BaseAgent, AgentResult
from models.task_request import TaskRequest
from runtime.checkpoint.checkpoint import AgentCheckpoint
from runtime.component import RuntimeComponent
from runtime.context import AgentExecutionContext
from runtime.context.runtime_context import RuntimeContext
from runtime.events.event import Event
from runtime.events.publisher import EventPublisher
from runtime.middleware.runtime_operation import RuntimeOperation


class AgentRuntime(RuntimeComponent):
    """
    Runtime responsible for Agent invocation.

    AgentRuntime is responsible for:

        - creating AgentExecutionContext
        - invoking an Agent
        - executing Runtime middleware
        - publishing Agent lifecycle events

    AgentRuntime does NOT own:

        - Agent decision making
        - Workflow control
        - Agent lifecycle
        - Agent registry

    A normal invocation creates a new AgentExecutionContext.

    A resumed invocation may provide an existing
    AgentExecutionContext restored from a Checkpoint.
    """

    def __init__(self, publisher: EventPublisher | None = None, middleware_chain =None):
        super().__init__(middleware_chain)
        self._publisher = publisher

    async def execute(
            self,
            agent: BaseAgent,
            task: TaskRequest,
            runtime_context: RuntimeContext,
            agent_execution_context: AgentExecutionContext | None = None,
    ) -> AgentResult:
        """
        Execute one Agent.

        Args:
            agent:
                Agent that should be invoked.
            task:
                Task being executed.
            runtime_context:
                Runtime-level context shared by all Agents
                participating in this execution.
            agent_execution_context:
                Optional existing AgentExecutionContext.

                If omitted, a new isolated execution context
                is created.

                If provided, the supplied context is reused.
                This allows an Agent execution to continue from
                a restored Checkpoint.

        Returns:
            AgentResult:
                Result returned by the Agent.

        Raises:
            Exception:
                Any exception raised by the Agent or Runtime
                middleware is propagated after the failure
                event is published.
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

        # ---------------------------------------------------------
        # Execution Context
        # ---------------------------------------------------------
        #
        # Normal execution:
        #
        #     no context supplied
        #          ↓
        #     create isolated context
        #
        # Resume execution:
        #
        #     restored context supplied
        #          ↓
        #     reuse restored context
        #
        if agent_execution_context is None:
            agent_execution_context = self._create_execution_context(
                runtime_context=runtime_context,
                agent=agent,
            )
        else:
            self._validate_execution_context(
                runtime_context=runtime_context,
                agent=agent,
                execution_context=agent_execution_context
            )

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
            raise

    def _create_execution_context(
            self,
            runtime_context: RuntimeContext,
            agent: BaseAgent,
    ) -> AgentExecutionContext:
        """
        Create a new execution-local context for one Agent invocation.

        This method is used only for normal execution.

        AgentContext and MemoryRuntime remain owned by the Agent.
        """
        return AgentExecutionContext.create(runtime_context, agent)

    def _restore_execution_context(
            self,
            runtime_context: RuntimeContext,
            agent: BaseAgent,
            checkpoint: AgentCheckpoint,
    ) -> AgentExecutionContext:
        """
        Restore execution-local state for one Agent invocation.

        The checkpoint contains execution-local state:

            - ContextState
            - LoopState

        The checkpoint does NOT replace:

            - AgentContext
            - MemoryRuntime
            - AgentIdentity

        Those continue to come from the live Agent instance.
        """
        self._validate_agent_checkpoint(agent, checkpoint)
        return AgentExecutionContext.restore(
            runtime_context=runtime_context,
            agent=agent,
            checkpoint=checkpoint,
        )

    def _validate_execution_context(
            self,
            runtime_context: RuntimeContext,
            agent: BaseAgent,
            execution_context: AgentExecutionContext,
    ) -> None:
        """
        Validate that an existing AgentExecutionContext belongs
        to the current Agent and Runtime execution.
        """
        if execution_context.agent_identity.agent_id != agent.identity.agent_id:
            raise ValueError(
                "AgentExecutionContext belongs to a different Agent:"
                f"{execution_context.agent_identity.agent_id}"
            )

        if execution_context.runtime_context.runtime_id != runtime_context.runtime_id:
            raise ValueError(
                "AgentExecutionContext belongs to a different RuntimeContext:"
            )

    def _validate_agent_checkpoint(
            self,
            agent: BaseAgent,
            checkpoint: AgentCheckpoint,
    ) -> None:
        """
        Validate that an AgentCheckpoint belongs to the Agent
        being recovered.
        """
        if checkpoint.agent_id != agent.identity.agent_id:
            raise ValueError(
                "Agent checkpoint identity mismatch: "
                f"checkpoint={checkpoint.agent_id}, "
                f"agent={agent.identity.agent_id}"
            )

    async def _publish(self, event: Event):
        """
        Publish an Agent lifecycle event.

        Event publishing is optional because AgentRuntime can
        operate without an EventPublisher in unit tests.
        """
        if self._publisher is None:
            return

        self._publisher.emit(event)