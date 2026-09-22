from __future__ import annotations

from agents.base_agent import BaseAgent
from models.task_request import TaskRequest
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
)
from runtime.checkpoint import Checkpoint
from runtime.execution import ExecutionHandle

from runtime.orchestration.orchestrator import (
    OrchestrationResult,
    Orchestrator,
)


class SingleAgentOrchestrator(Orchestrator):
    """
    Compatibility Orchestrator for the current AgentOS application model.

    The selected entry Agent may itself be a SupervisorAgent.

    Therefore:

        SingleAgentOrchestrator
                |
                v
        SupervisorAgent
                |
                +---- ResearchAgent
                +---- Future Agents

    This class does NOT mean that AgentOS is limited to one Agent.

    It provides the orchestration boundary required by ApplicationExecutor
    while preserving the current SupervisorAgent implementation.
    """

    ENTRY_AGENT_METADATA_KEY = "orchestrator_agent_id"

    def resolve_entry_agent(self) -> BaseAgent:
        agents = self._application.agents

        if not agents:
            raise ApplicationLifecycleError(
                "Application cannot execute a task because no Agent "
                "is registered."
            )

        if len(agents) > 1:
            raise ApplicationLifecycleError(
                "SingleAgentOrchestrator cannot resolve an entry Agent "
                "because multiple Agents are registered. "
                "Configure a concrete orchestration strategy."
            )

        return agents[0]

    async def execute(
        self,
        task: TaskRequest,
        execution_handle: ExecutionHandle,
    ) -> OrchestrationResult:
        agent = self.resolve_entry_agent()

        result = await self._application.invoke_agent(
            agent_id=agent.identity.agent_id,
            task=task,
            execution_handle=execution_handle,
        )

        return OrchestrationResult(
            agent=agent,
            agent_result=result,
        )

    async def resume(
        self,
        task: TaskRequest,
        execution_handle: ExecutionHandle,
        checkpoint: Checkpoint,
        entry_agent_id: str,
    ) -> OrchestrationResult:
        """
        Resume the persisted orchestration entry Agent.

        The Agent is identified by the durable Execution metadata.

        Its execution-local state is restored from the corresponding
        AgentCheckpoint before AgentRuntime.execute() continues.
        """

        agent = self._application.get_agent(entry_agent_id)

        agent_checkpoint = checkpoint.agents.get(
            entry_agent_id
        )

        if agent_checkpoint is None:
            raise ApplicationLifecycleError(
                "Checkpoint does not contain an AgentCheckpoint "
                f"for orchestration entry Agent: {entry_agent_id}"
            )

        agent_execution_context = (
            self._application.agent_runtime.restore_execution_context(
                runtime_context=execution_handle.runtime_context,
                agent=agent,
                checkpoint=agent_checkpoint,
            )
        )

        result = await self._application.agent_runtime.execute(
            agent=agent,
            task=task,
            runtime_context=execution_handle.runtime_context,
            agent_execution_context=agent_execution_context,
        )

        return OrchestrationResult(
            agent=agent,
            agent_result=result,
        )