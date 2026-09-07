from __future__ import annotations

from agents import AgentResult
from agents.base_agent import BaseAgent
from models.task_request import TaskRequest
from models.task_result import TaskResult
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
)
from runtime.execution.execution_runtime import ExecutionRuntime


class ApplicationExecutor:
    """
    Internal execution adapter for AgentApplication.

    This class hides low-level execution lifecycle details from the
    public Application API.

    Current Phase 12 behavior:
    - create one Execution
    - select one default Agent
    - invoke that Agent through AgentApplication
    - close the Execution

    Future versions may replace the default-agent path with a
    Supervisor / Workflow execution orchestrator without changing
    AgentApplication.execute().
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
    ):
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