from __future__ import annotations

from agents.base_agent import BaseAgent
from models.task_request import TaskRequest
from runtime.agents.agent_registry import AgentRegistry
from runtime.checkpoint import Checkpoint
from runtime.execution import AgentRuntime, ExecutionHandle
from runtime.orchestration.orchestration_error import OrchestrationError

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

    It provides the orchestration boundary required by
    ApplicationExecutor while preserving the current SupervisorAgent
    implementation.
    """

    ENTRY_AGENT_METADATA_KEY = "orchestrator_agent_id"

    def __init__(
        self,
        agent_registry: AgentRegistry,
        agent_runtime: AgentRuntime,
    ) -> None:
        super().__init__(
            agent_registry=agent_registry,
            agent_runtime=agent_runtime,
        )

    def resolve_entry_agent(self) -> BaseAgent:
        agents = self._agent_registry.all()

        if not agents:
            raise OrchestrationError(
                "Application cannot execute a task because no Agent "
                "is registered."
            )

        if len(agents) > 1:
            raise OrchestrationError(
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

        result = await self._agent_runtime.execute(
            agent=agent,
            task=task,
            runtime_context=execution_handle.runtime_context,
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

        The Agent is identified by durable Execution metadata.

        Its execution-local state is restored from the corresponding
        AgentCheckpoint before AgentRuntime.execute() continues.
        """

        agent = self._agent_registry.get(entry_agent_id)

        agent_checkpoint = checkpoint.agents.get(
            entry_agent_id
        )

        if agent_checkpoint is None:
            raise OrchestrationError(
                "Checkpoint does not contain an AgentCheckpoint "
                f"for orchestration entry Agent: {entry_agent_id}"
            )

        agent_execution_context = (
            self._agent_runtime.restore_execution_context(
                runtime_context=execution_handle.runtime_context,
                agent=agent,
                checkpoint=agent_checkpoint,
            )
        )

        result = await self._agent_runtime.execute(
            agent=agent,
            task=task,
            runtime_context=execution_handle.runtime_context,
            agent_execution_context=agent_execution_context,
        )

        return OrchestrationResult(
            agent=agent,
            agent_result=result,
        )