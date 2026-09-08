from __future__ import annotations

from agents import AgentResult
from agents.base_agent import BaseAgent
from models.task_request import TaskRequest
from models.task_result import TaskResult
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
)
from runtime.checkpoint import Checkpoint
from runtime.execution import ExecutionHandle
from runtime.execution.execution_runtime import ExecutionRuntime


class ApplicationExecutor:
    """
    Internal execution adapter for AgentApplication.

    This class hides low-level execution lifecycle details from the
    public Application API.

    Responsibilities:
        - create ExecutionHandle for normal execution
        - recover ExecutionHandle from Checkpoint
        - resume a specific Agent execution from Checkpoint
        - close ExecutionHandle after normal execution

    ApplicationExecutor does NOT own:
        - Checkpoint persistence
        - AgentContext
        - MemoryRuntime
        - Agent scheduling
        - Workflow decisions

    The explicit ``agent_id`` used by recovery is a temporary
    capability-validation mechanism.

    A future Workflow Runtime will determine which Agent should
    resume automatically.
    """

    def __init__(
        self,
        application,
        execution_runtime: ExecutionRuntime,
    ) -> None:
        self._application = application
        self._execution_runtime = execution_runtime

    async def execute(
        self,
        task: TaskRequest,
    ) -> TaskResult:
        """
        Execute a new Application task.

        ExecutionHandle is always closed in finally.
        """
        execution_handle = self._execution_runtime.create_execution()

        try:
            agent = self._select_default_agent()

            agent_result = await self._application.invoke_agent(
                agent_id=agent.identity.agent_id,
                task=task,
                execution_handle=execution_handle,
            )

            return self._to_task_result(task, agent, agent_result)
        finally:
            await execution_handle.close()

    async def recover_execution(
            self,
            checkpoint: Checkpoint,
    ) -> ExecutionHandle:
        """
        Recover an existing Execution from a Checkpoint.

        This method reconstructs the ExecutionHandle but does not
        execute an Agent.

        The caller owns the returned handle and is responsible
        for closing it.

        This is the low-level Application recovery primitive.
        """
        return self._execution_runtime.resume_execution(checkpoint)

    async def recover_agent_execution(
            self,
            checkpoint: Checkpoint,
            agent_id: str,
            task: TaskRequest
    ) -> AgentResult:
        """
        Resume one Agent execution from a Checkpoint.

        Recovery flow:

            Checkpoint
                |
                v
            ExecutionHandle
                |
                v
            restored RuntimeContext
                |
                v
            AgentCheckpoint
                |
                v
            AgentExecutionContext
                |
                v
            AgentRuntime
                |
                v
            Agent

        The Agent instance is resolved from the Application's
        existing Agent registry.

        The Agent instance itself is NOT recreated.

        This method is intentionally an internal recovery primitive.
        Workflow-level Agent selection will be introduced later.
        """

        execution_handle = await self.recover_execution(checkpoint=checkpoint)

        try:
            agent = self._application.get_agent(agent_id)
            agent_checkpoint = checkpoint.agents.get(agent.identity.agent_id)

            if agent_checkpoint is None:
                raise ApplicationLifecycleError(
                    f"Checkpoint does not contain an AgentCheckpoint for Agent: {agent_id}"
                )

            agent_execution_context = (
                self._application.agent_runtime.restore_execution_context(
                    runtime_context=execution_handle.runtime_context,
                    agent=agent,
                    checkpoint=agent_checkpoint
            ))

            return await self._application.agent_runtime.execute(
                agent,
                task,
                execution_handle.runtime_context,
                agent_execution_context,
            )
        finally:
            await execution_handle.close()

    def _select_default_agent(self) -> BaseAgent:
        agents = self._application.agents

        if not agents:
            raise ApplicationLifecycleError(
                "Application cannot execute a task because no Agent is registered."
            )

        if len(agents) > 1:
            raise ApplicationLifecycleError(
                "Application cannot select a default Agent because multiple "
                "Agents are registered."
            )

        return agents[0]

    def _to_task_result(
            self,
            task: TaskRequest,
            agent: BaseAgent,
            agent_result: AgentResult,
    ) -> TaskResult:
        return TaskResult(
            success=agent_result.success,
            answer=agent_result.output or "",
            metadata={
                "task_id": task.task_id,
                "agent_id":agent.identity.agent_id,
                "agent_type": agent.identity.agent_type
            }
        )