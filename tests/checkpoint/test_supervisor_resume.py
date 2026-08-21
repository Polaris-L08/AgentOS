from __future__ import annotations

import pytest

from agents.identity import AgentIdentity
from agents.research.research_agent import ResearchAgent
from agents.supervisor_agent import SupervisorAgent
from models.task_request import TaskRequest
from providers.llm_provider import LLMProvider
from providers.llm_response import LLMResponse
from providers.prompt_message import PromptMessage
from runtime.checkpoint.checkpoint_coordinator import (
    CheckpointCoordinator,
)
from runtime.checkpoint.memory_checkpoint_store import (
    MemoryCheckpointStore,
)
from runtime.context.agent_execution_context import (
    AgentExecutionContext,
)
from runtime.context.shared_context import SharedContext
from runtime.events.event_bus import EventBus
from runtime.execution import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.loop.loop_state import LoopState
from runtime.tracing.trace_recorder import TraceRecorder
from tools.base import AbstractTool
from tools.registry import ToolRegistry
from tools.result import ToolResult
from tools.tool_executor import ToolExecutor


class MarketResearchTool(AbstractTool):
    """
    Concrete research Tool used by the integration test.
    """

    @property
    def name(self) -> str:
        return "market_research"

    @property
    def description(self) -> str:
        return "Retrieve market research data."

    async def execute(
        self,
        input,
        context_state,
    ) -> ToolResult:
        return ToolResult(
            success=True,
            output={
                "subject": input["subject"],
                "objective": input["objective"],
                "market_data": (
                    f"Research data for {input['subject']}."
                ),
            },
            metadata={
                "source": "test_market_data_provider",
            },
        )


class SequentialLLMProvider(LLMProvider):
    """
    Deterministic LLM provider.

    The first response is used during the original execution.

    The second response is used after checkpoint recovery.
    """

    def __init__(
        self,
        responses: list[str],
    ) -> None:
        self._responses = list(responses)
        self._index = 0

    async def generate(
        self,
        messages: list[PromptMessage],
    ) -> LLMResponse:

        if self._index >= len(self._responses):
            raise RuntimeError(
                "SequentialLLMProvider has no more responses."
            )

        response = self._responses[self._index]

        self._index += 1

        return LLMResponse(
            content=response,
        )


def create_runtime_context():
    """
    Create a fresh RuntimeContext for one execution.
    """

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    return execution_runtime.create_context()


def create_research_agent() -> ResearchAgent:
    """
    Create the ResearchAgent used by the test.
    """

    registry = ToolRegistry()

    registry.register(
        MarketResearchTool()
    )

    event_bus = EventBus()

    tool_executor = ToolExecutor(
        registry,
        event_bus,
    )

    return ResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent-001",
            agent_type="investment_research",
            name="ResearchAgent",
        ),
        tool_executor=tool_executor,
        llm_provider=SequentialLLMProvider(
            responses=[
                "market_research",
                "final",
            ]
        ),
    )


@pytest.mark.asyncio
async def test_supervisor_can_resume_from_checkpoint():
    """
    Verify Multi-Agent Checkpoint Resume.

    Scenario:

        Supervisor
            |
            +-- ResearchAgent
            |
            +-- Research result written to SharedContext
            |
            +-- Supervisor Observation
            |
            +-- Checkpoint
            |
            X simulated process interruption
            |
            +-- Restore
            |
            +-- Supervisor resumes
            |
            +-- Supervisor decides final

    Important:

        The Runtime does not store a completed-agent list.

        The Supervisor reconstructs its decision from:

            1. restored Supervisor AgentExecutionContext
            2. restored SharedContext
    """

    task = TaskRequest(
        task_id="resume-test-001",
        user_input="Analyze NVIDIA stock",
    )

    runtime_context = create_runtime_context()

    agent_runtime = AgentRuntime()

    research_agent = create_research_agent()

    supervisor_llm = SequentialLLMProvider(
        responses=[
            "research",
            "final",
        ]
    )

    supervisor_agent = SupervisorAgent(
        identity=AgentIdentity(
            agent_id="supervisor-agent-001",
            agent_type="supervisor",
            name="SupervisorAgent",
        ),
        agent_runtime=agent_runtime,
        research_agent=research_agent,
        llm_provider=supervisor_llm,
    )

    # ---------------------------------------------------------
    # First execution
    # ---------------------------------------------------------

    supervisor_context = AgentExecutionContext.create(
        runtime_context,
        supervisor_agent.identity,
    )

    # Execute ResearchAgent through Supervisor.
    #
    # We intentionally do not let the Supervisor finish its
    # second decision here. The purpose is to create a realistic
    # intermediate execution state.
    research_result = await agent_runtime.execute(
        agent=research_agent,
        task=task,
        runtime_context=runtime_context,
    )

    assert research_result.success

    supervisor_observation = (
        supervisor_agent._create_agent_observation(
            research_result
        )
    )

    supervisor_context.loop.step_count = 1

    supervisor_context.loop.observation_history.append(
        supervisor_observation
    )

    # ResearchAgent writes the ResearchReport into SharedContext.
    assert (
        runtime_context.shared_context.get(
            ResearchAgent.RESEARCH_REPORT_KEY
        )
        is not None
    )

    # ---------------------------------------------------------
    # Create checkpoint
    # ---------------------------------------------------------

    checkpoint_coordinator = CheckpointCoordinator()

    checkpoint = checkpoint_coordinator.create_checkpoint(
        runtime_context=runtime_context,
        agent_execution_contexts={
            supervisor_agent.identity.agent_id:
                supervisor_context,
        },
        task_id=task.task_id,
    )

    store = MemoryCheckpointStore()

    await store.save(
        checkpoint.checkpoint_id,
        checkpoint,
    )

    # ---------------------------------------------------------
    # Simulate process interruption
    # ---------------------------------------------------------

    del supervisor_context
    del runtime_context

    # ---------------------------------------------------------
    # Restore
    # ---------------------------------------------------------

    restored_checkpoint = await store.load(
        checkpoint.checkpoint_id,
    )

    assert restored_checkpoint is not None

    restored_runtime_context = create_runtime_context()

    # The restored execution must use the checkpoint's shared
    # context rather than creating an empty SharedContext.
    restored_runtime_context.shared_context.data.update(
        restored_checkpoint.shared_context.data
    )

    restored_contexts = (
        checkpoint_coordinator.restore_agent_contexts(
            checkpoint=restored_checkpoint,
            agents={
                supervisor_agent.identity.agent_id:
                    supervisor_agent,
            },
            runtime_context=restored_runtime_context,
        )
    )

    restored_supervisor_context = restored_contexts[
        supervisor_agent.identity.agent_id
    ]

    # ---------------------------------------------------------
    # Verify restored state
    # ---------------------------------------------------------

    assert (
        restored_supervisor_context.loop.step_count
        == 1
    )

    assert len(
        restored_supervisor_context.loop.observation_history
    ) == 1

    assert (
        restored_runtime_context.shared_context.get(
            ResearchAgent.RESEARCH_REPORT_KEY
        )
        is not None
    )

    # ---------------------------------------------------------
    # Resume Supervisor
    # ---------------------------------------------------------

    result = await agent_runtime.execute(
        agent=supervisor_agent,
        task=task,
        runtime_context=restored_runtime_context,
        agent_execution_context=restored_supervisor_context,
    )

    assert result.success

    # Supervisor had already executed the Research step.
    # After restore it receives "final" from the deterministic
    # LLM and therefore does not invoke ResearchAgent again.
    assert (
        supervisor_llm._index == 2
    )

    assert (
        restored_supervisor_context.loop.step_count
        == 2
    )

    assert len(
        restored_supervisor_context.loop.observation_history
    ) == 1