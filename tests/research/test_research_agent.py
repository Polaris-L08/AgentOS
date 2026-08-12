from __future__ import annotations

import pytest

from agents.agent_result import AgentResult
from agents.identity import AgentIdentity
from agents.research.domain.report import ResearchReport
from agents.research.domain.task import ResearchTask
from agents.research.research_agent import ResearchAgent
from runtime.context.agent_execution_context import AgentExecutionContext
from runtime.context.context_state import ContextState
from runtime.context.runtime_context import RuntimeContext
from runtime.context.shared_context import SharedContext
from runtime.loop.loop_state import LoopState
from runtime.tracing.trace import Trace
from runtime.tracing.trace_context import TraceContext
from runtime.tracing.trace_recorder import TraceRecorder


def create_runtime_context() -> RuntimeContext:
    """
    Create a RuntimeContext for direct Agent testing.

    This follows the same RuntimeContext structure
    used by the AgentOS runtime.
    """

    recorder = TraceRecorder()

    trace = Trace(
        trace_id="test-trace",
    )

    trace_context = TraceContext(
        recorder=recorder,
        trace=trace,
    )

    return RuntimeContext(
        trace=trace_context,
        shared_context=SharedContext(),
    )


def create_agent_execution_context(
    agent: ResearchAgent,
) -> AgentExecutionContext:
    """
    Create an isolated execution context for one Agent.
    """

    runtime_context = create_runtime_context()

    return AgentExecutionContext(
        runtime_context=runtime_context,
        agent_identity=agent.identity,
        state=ContextState(),
        loop=LoopState(),
    )


@pytest.mark.asyncio
async def test_research_agent_run():

    agent = ResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent-001",
            agent_type="research",
            name="ResearchAgent",
        )
    )

    task = ResearchTask(
        task_id="research-task-001",
        subject="NVIDIA",
        objective="Evaluate the investment outlook.",
    )

    execution_context = create_agent_execution_context(agent)

    result = await agent.run(
        task=task,
        agent_execution_context=execution_context,
    )

    assert isinstance(result, AgentResult)

    assert result.success is True

    assert isinstance(
        result.output,
        ResearchReport,
    )

    report = result.output

    assert report.task_id == "research-task-001"

    assert report.subject == "NVIDIA"

    assert (
        report.summary
        == (
            "Research completed for NVIDIA. "
            "Objective: Evaluate the investment outlook."
        )
    )


@pytest.mark.asyncio
async def test_research_agent_execute():

    agent = ResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent-001",
            agent_type="research",
            name="ResearchAgent",
        )
    )

    task = ResearchTask(
        task_id="research-task-001",
        subject="NVIDIA",
        objective="Evaluate the investment outlook.",
    )

    execution_context = create_agent_execution_context(agent)

    result = await agent.execute(
        task=task,
        agent_execution_context=execution_context,
    )

    assert isinstance(result, AgentResult)

    assert result.success is True

    assert isinstance(
        result.output,
        ResearchReport,
    )

    assert result.output.subject == "NVIDIA"