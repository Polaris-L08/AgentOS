from __future__ import annotations

import pytest

from actions.observation import Observation
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from runtime.checkpoint.checkpoint_coordinator import (
    CheckpointCoordinator,
)
from runtime.context.agent_execution_context import (
    AgentExecutionContext,
)
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):

    async def run(
        self,
        task,
        agent_execution_context,
    ):
        raise NotImplementedError


def create_agent(
    agent_id: str,
    agent_type: str,
    name: str,
):
    return MockAgent(
        identity=AgentIdentity(
            agent_id=agent_id,
            agent_type=agent_type,
            name=name,
        )
    )


def create_runtime_context():

    execution_runtime = ExecutionRuntime(
        TraceRecorder()
    )

    return execution_runtime.create_context()


@pytest.mark.asyncio
async def test_create_multi_agent_checkpoint():

    runtime_context = create_runtime_context()

    supervisor = create_agent(
        "supervisor-agent",
        "supervisor",
        "SupervisorAgent",
    )

    research = create_agent(
        "research-agent",
        "research",
        "ResearchAgent",
    )

    supervisor_context = AgentExecutionContext.create(
        runtime_context,
        supervisor.identity,
    )

    research_context = AgentExecutionContext.create(
        runtime_context,
        research.identity,
    )

    supervisor_context.loop.step_count = 3

    supervisor_context.loop.observation_history.append(
        Observation(
            success=True,
            content="Supervisor analyzed task.",
        )
    )

    research_context.loop.step_count = 2

    research_context.loop.observation_history.append(
        Observation(
            success=True,
            content="Research completed.",
        )
    )

    runtime_context.shared_context.set(
        "research.report",
        "NVIDIA research result",
    )

    agent_contexts = {
        supervisor.identity.agent_id: supervisor_context,
        research.identity.agent_id: research_context,
    }

    coordinator = CheckpointCoordinator()

    checkpoint = coordinator.create_checkpoint(
        runtime_context=runtime_context,
        agent_execution_contexts=agent_contexts,
        task_id="task-001",
    )

    assert checkpoint.runtime_id == runtime_context.runtime_id

    assert checkpoint.task_id == "task-001"

    assert (
        checkpoint.shared_context.get("research.report")
        == "NVIDIA research result"
    )

    assert set(checkpoint.agents.keys()) == {
        "supervisor-agent",
        "research-agent",
    }

    assert (
        checkpoint.agents["supervisor-agent"]
        .loop.step_count
        == 3
    )

    assert (
        checkpoint.agents["research-agent"]
        .loop.step_count
        == 2
    )

    assert (
        checkpoint.agents["supervisor-agent"]
        .loop.observation_history[0]
        .content
        == "Supervisor analyzed task."
    )

    assert (
        checkpoint.agents["research-agent"]
        .loop.observation_history[0]
        .content
        == "Research completed."
    )

@pytest.mark.asyncio
async def test_checkpoint_is_snapshot():

    runtime_context = create_runtime_context()

    research = create_agent(
        "research-agent",
        "research",
        "ResearchAgent",
    )

    research_context = AgentExecutionContext.create(
        runtime_context,
        research.identity,
    )

    research_context.loop.step_count = 1

    research_context.loop.observation_history.append(
        Observation(
            success=True,
            content="Initial research.",
        )
    )

    runtime_context.shared_context.set(
        "research.status",
        "running",
    )

    coordinator = CheckpointCoordinator()

    checkpoint = coordinator.create_checkpoint(
        runtime_context=runtime_context,
        agent_execution_contexts={
            research.identity.agent_id: research_context,
        },
    )

    # -----------------------------------------
    # Continue execution after checkpoint
    # -----------------------------------------

    research_context.loop.step_count = 10

    research_context.loop.observation_history.append(
        Observation(
            success=True,
            content="Later research.",
        )
    )

    runtime_context.shared_context.set(
        "research.status",
        "completed",
    )

    # -----------------------------------------
    # Checkpoint must remain unchanged
    # -----------------------------------------

    assert (
        checkpoint.agents["research-agent"]
        .loop.step_count
        == 1
    )

    assert len(
        checkpoint.agents["research-agent"]
        .loop.observation_history
    ) == 1

    assert (
        checkpoint.agents["research-agent"]
        .loop.observation_history[0]
        .content
        == "Initial research."
    )

    assert (
        checkpoint.shared_context.get(
            "research.status"
        )
        == "running"
    )