from __future__ import annotations

from copy import deepcopy

from agents import BaseAgent
from runtime.checkpoint.checkpoint import (
    AgentCheckpoint,
    Checkpoint,
)
from runtime.context.agent_execution_context import (
    AgentExecutionContext,
)
from runtime.context.runtime_context import RuntimeContext


class CheckpointCoordinator:
    """
    Execution-level checkpoint coordinator.

    Responsible for creating a consistent snapshot of one
    Multi-Agent execution.

    It does NOT:
        - execute Agents
        - manage Agent lifecycle
        - persist checkpoints
        - control workflow execution

    It only converts the current execution state into a
    Checkpoint snapshot.
    """

    def create_checkpoint(
        self,
        runtime_context: RuntimeContext,
        agent_execution_contexts: dict[
            str,
            AgentExecutionContext,
        ],
        task_id: str | None = None,
    ) -> Checkpoint:
        """
        Create an execution-level checkpoint.

        All AgentExecutionContexts participating in the same
        execution are captured in one Checkpoint.
        """

        agents: dict[str, AgentCheckpoint] = {}

        for agent_id, execution_context in agent_execution_contexts.items():

            if agent_id != execution_context.agent_identity.agent_id:
                raise ValueError(
                    "AgentExecutionContext key does not match "
                    "AgentIdentity.agent_id."
                )

            agents[agent_id] = AgentCheckpoint(
                agent_id=agent_id,
                state=deepcopy(execution_context.state),
                loop=deepcopy(execution_context.loop),
            )

        return Checkpoint(
            runtime_id=runtime_context.runtime_id,
            shared_context=deepcopy(
                runtime_context.shared_context
            ),
            agents=agents,
            task_id=task_id,
        )

    def restore_agent_contexts(
            self,
            checkpoint: Checkpoint,
            agents: dict[str, BaseAgent],
            runtime_context: RuntimeContext,
    ) -> dict[str, AgentExecutionContext]:

        contexts = {}

        for agent_id, agent_checkpoint in checkpoint.agents.items():

            agent = agents.get(agent_id)

            if agent is None:
                raise ValueError(
                    f"Agent not found: {agent_id}"
                )

            context = AgentExecutionContext(
                runtime_context=runtime_context,
                agent_identity=agent.identity,
                agent_context=agent.context,
                memory=agent.memory,
                state=deepcopy(agent_checkpoint.state),
                loop=deepcopy(agent_checkpoint.loop),
            )

            contexts[agent_id] = context

        return contexts