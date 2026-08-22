from __future__ import annotations

from typing import Any

import pytest

from agents.agent_result import AgentResult
from agents.identity import AgentIdentity
from agents.research.research_agent import ResearchAgent
from agents.supervisor_agent import SupervisorAgent
from models.task_request import TaskRequest
from providers.llm_provider import LLMProvider
from providers.llm_response import LLMResponse
from providers.prompt_message import PromptMessage
from runtime.checkpoint.checkpoint_coordinator import CheckpointCoordinator
from runtime.checkpoint.memory_checkpoint_store import MemoryCheckpointStore
from runtime.context.agent_execution_context import AgentExecutionContext
from runtime.context.runtime_context import RuntimeContext
from runtime.events.event_bus import EventBus
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder
from tools.base import AbstractTool
from tools.registry import ToolRegistry
from tools.request import ToolRequest
from tools.result import ToolResult
from tools.tool_executor import ToolExecutor


# ============================================================
# Test Tool
# ============================================================


class MarketResearchTool(AbstractTool):
    """
    Deterministic Tool used by ResearchAgent during the test.

    This represents a concrete Tool implementation rather than
    mocking the Tool Runtime itself.

    ResearchAgent
        ↓
    ToolExecutor
        ↓
    MarketResearchTool
    """

    @property
    def name(self) -> str:
        return "market_research"

    @property
    def description(self) -> str:
        return "Retrieve market research data for a subject."

    async def execute(
        self,
        input: Any,
        context_state,
    ) -> ToolResult:
        """
        Return deterministic research data.

        No external system is accessed during the test.
        """

        subject = input["subject"]
        objective = input["objective"]

        return ToolResult(
            success=True,
            output={
                "subject": subject,
                "objective": objective,
                "market_data": (
                    f"Research data collected for {subject}."
                ),
            },
            metadata={
                "source": "test_market_data_provider",
            },
        )


# ============================================================
# Test LLM Providers
# ============================================================


class ResearchLLMProvider(LLMProvider):
    """
    Deterministic LLM provider for ResearchAgent.

    ResearchAgent requires:

        1. market_research
        2. final

    Therefore the provider returns these decisions in order.
    """

    def __init__(self) -> None:
        self.calls = 0

    async def generate(
        self,
        messages: list[PromptMessage],
    ) -> LLMResponse:

        self.calls += 1

        if self.calls == 1:
            return LLMResponse(
                content="market_research"
            )

        if self.calls == 2:
            return LLMResponse(
                content="final"
            )

        raise RuntimeError(
            "ResearchLLMProvider received an unexpected "
            "additional invocation."
        )


class CrashAfterResearchLLMProvider(LLMProvider):
    """
    Supervisor LLM provider used during the first execution.

    Expected sequence:

        first decision
            ↓
        research

        second decision
            ↓
        simulated process crash

    The crash happens AFTER ResearchAgent has completed.

    This is important because the checkpoint must contain:

        - Research result in SharedContext
        - Research Observation in Supervisor LoopState

    when the process fails.
    """

    def __init__(self) -> None:
        self.calls = 0

    async def generate(
        self,
        messages: list[PromptMessage],
    ) -> LLMResponse:

        self.calls += 1

        if self.calls == 1:
            return LLMResponse(
                content="research"
            )

        raise RuntimeError(
            "Simulated process crash after ResearchAgent."
        )


class ResumeSupervisorLLMProvider(LLMProvider):
    """
    Supervisor LLM provider used after Resume.

    The restored Supervisor already has the ResearchAgent result,
    so the Supervisor should continue directly to final.

    Expected sequence:

        final
    """

    def __init__(self) -> None:
        self.calls = 0

    async def generate(
        self,
        messages: list[PromptMessage],
    ) -> LLMResponse:

        self.calls += 1

        return LLMResponse(
            content="final"
        )


# ============================================================
# Test Supervisor
# ============================================================


class InspectableSupervisorAgent(SupervisorAgent):
    """
    SupervisorAgent used to expose its AgentExecutionContext
    to the integration test.

    The production SupervisorAgent should NOT manage or expose
    execution contexts.

    This subclass exists only because the integration test needs
    to capture the execution state at the moment of the simulated
    crash.

    Production architecture remains:

        AgentRuntime
            ↓
        AgentExecutionContext

    The test merely observes that state.
    """

    def __init__(
        self,
        identity: AgentIdentity,
        agent_runtime: AgentRuntime,
        research_agent: ResearchAgent,
        llm_provider: LLMProvider,
    ) -> None:
        super().__init__(
            identity=identity,
            agent_runtime=agent_runtime,
            research_agent=research_agent,
            llm_provider=llm_provider,
        )

        self.execution_context: (
            AgentExecutionContext | None
        ) = None

    async def run(
        self,
        task: TaskRequest,
        agent_execution_context: AgentExecutionContext,
    ) -> AgentResult:

        self.execution_context = agent_execution_context

        return await super().run(
            task,
            agent_execution_context,
        )


# ============================================================
# Test Helpers
# ============================================================


def create_runtime_context() -> RuntimeContext:
    """
    Create a RuntimeContext using the same mechanism used by
    the real ExecutionRuntime.
    """

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    return execution_runtime.create_context()


def create_research_agent(
    event_bus: EventBus,
) -> ResearchAgent:
    """
    Create the ResearchAgent used in the integration test.

    The Agent uses the real:

        ResearchAgent
        ToolExecutor
        ToolRegistry
        Tool

    Only the external LLM decision is deterministic.
    """

    registry = ToolRegistry()

    registry.register(
        MarketResearchTool()
    )

    tool_executor = ToolExecutor(
        registry=registry,
        publisher=event_bus,
    )

    return ResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent-001",
            agent_type="investment_research",
            name="ResearchAgent",
        ),
        tool_executor=tool_executor,
        llm_provider=ResearchLLMProvider(),
    )


def create_task() -> TaskRequest:
    """
    Create the user task used throughout the test.
    """

    return TaskRequest(
        task_id="task-resume-001",
        user_input="Analyze NVIDIA stock",
    )


# ============================================================
# Integration Test
# ============================================================


@pytest.mark.asyncio
async def test_multi_agent_checkpoint_resume():
    """
    Verify Multi-Agent Checkpoint / Resume.

    Scenario:

        User Request
             ↓
        Supervisor
             ↓
        ResearchAgent
             ↓
        ResearchAgent Result
             ↓
        SharedContext
             ↓
        Supervisor execution state
             ↓
        Checkpoint
             ↓
        simulated process crash
             ↓
        Restore
             ↓
        Supervisor
             ↓
        final

    The most important acceptance criterion is:

        ResearchAgent must NOT execute again after Resume.

    This proves that the resumed Supervisor uses its restored
    execution state and SharedContext rather than restarting the
    previous Agent invocation.
    """

    # ========================================================
    # 1. Runtime setup
    # ========================================================

    event_bus = EventBus()

    agent_runtime = AgentRuntime(
        publisher=event_bus,
    )

    runtime_context = create_runtime_context()

    task = create_task()

    research_agent = create_research_agent(
        event_bus
    )

    # ========================================================
    # 2. First Supervisor execution
    #
    # Supervisor:
    #
    #     research
    #
    # ResearchAgent:
    #
    #     market_research
    #     final
    #
    # Supervisor then asks for another decision.
    #
    # The second Supervisor LLM call simulates a process crash.
    # ========================================================

    first_supervisor = InspectableSupervisorAgent(
        identity=AgentIdentity(
            agent_id="supervisor-agent-001",
            agent_type="supervisor",
            name="SupervisorAgent",
        ),
        agent_runtime=agent_runtime,
        research_agent=research_agent,
        llm_provider=CrashAfterResearchLLMProvider(),
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated process crash",
    ):
        await agent_runtime.execute(
            agent=first_supervisor,
            task=task,
            runtime_context=runtime_context,
        )

    # ========================================================
    # 3. Verify the state BEFORE checkpoint
    # ========================================================

    assert first_supervisor.execution_context is not None

    supervisor_context = (
        first_supervisor.execution_context
    )

    # Supervisor executed:
    #
    #   Step 1 -> research
    #   Step 2 -> crash
    #
    assert supervisor_context.loop.step_count == 2

    # ResearchAgent must have produced one observation.
    assert len(
        supervisor_context.loop.observation_history
    ) == 1

    observation = supervisor_context.loop.observation_history[0]

    assert observation.success is True

    # ResearchAgent writes its ResearchReport into
    # RuntimeContext.shared_context.
    research_report = (
        runtime_context.shared_context.get(
            ResearchAgent.RESEARCH_REPORT_KEY
        )
    )

    assert research_report is not None

    # ========================================================
    # 4. Create Checkpoint
    # ========================================================

    checkpoint_coordinator = (
        CheckpointCoordinator()
    )

    checkpoint = (
        checkpoint_coordinator.create_checkpoint(
            runtime_context=runtime_context,
            agent_execution_contexts={
                first_supervisor.identity.agent_id:
                    supervisor_context,
            },
            task_id=task.task_id,
        )
    )

    assert checkpoint.runtime_id == (
        runtime_context.runtime_id
    )

    assert checkpoint.task_id == task.task_id

    # SharedContext must be persisted.
    assert (
        checkpoint.shared_context.get(
            ResearchAgent.RESEARCH_REPORT_KEY
        )
        is not None
    )

    # Supervisor execution state must be persisted.
    assert (
        "supervisor-agent-001"
        in checkpoint.agents
    )

    supervisor_checkpoint = checkpoint.agents[
        "supervisor-agent-001"
    ]

    assert (
        supervisor_checkpoint.loop.step_count
        == supervisor_context.loop.step_count
    )

    assert (
        len(
            supervisor_checkpoint.loop.observation_history
        )
        == 1
    )

    # ========================================================
    # 5. Persist Checkpoint
    # ========================================================

    checkpoint_store = MemoryCheckpointStore()

    await checkpoint_store.save(
        checkpoint.checkpoint_id,
        checkpoint,
    )

    # Simulate the process losing the original runtime state.
    #
    # We intentionally do NOT reuse:
    #
    #     runtime_context
    #     supervisor_context
    #
    # for the resumed execution.
    #
    # The only source of execution state after this point is
    # the persisted Checkpoint.
    restored_checkpoint = (
        await checkpoint_store.load(
            checkpoint.checkpoint_id
        )
    )

    assert restored_checkpoint is not None

    # ========================================================
    # 6. Reconstruct RuntimeContext
    # ========================================================
    #
    # RuntimeContext contains:
    #
    #     runtime_id
    #     SharedContext
    #     TraceContext
    #
    # Shared execution state comes from Checkpoint.
    #
    # TraceContext is runtime infrastructure and is created
    # again for the resumed execution.
    # ========================================================

    resumed_execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    fresh_runtime_context = (
        resumed_execution_runtime.create_context()
    )

    resumed_runtime_context = RuntimeContext(
        trace=fresh_runtime_context.trace,
        shared_context=(
            restored_checkpoint.shared_context
        ),
        runtime_id=restored_checkpoint.runtime_id,
    )

    # Runtime identity must be preserved.
    assert (
        resumed_runtime_context.runtime_id
        == runtime_context.runtime_id
    )

    # Shared research result must be restored.
    assert (
        resumed_runtime_context.shared_context.get(
            ResearchAgent.RESEARCH_REPORT_KEY
        )
        is not None
    )

    # ========================================================
    # 7. Restore Supervisor AgentExecutionContext
    # ========================================================

    resumed_supervisor = InspectableSupervisorAgent(
        identity=AgentIdentity(
            agent_id="supervisor-agent-001",
            agent_type="supervisor",
            name="SupervisorAgent",
        ),
        agent_runtime=agent_runtime,
        research_agent=research_agent,
        llm_provider=ResumeSupervisorLLMProvider(),
    )

    restored_contexts = (
        checkpoint_coordinator.restore_agent_contexts(
            checkpoint=restored_checkpoint,
            agents={
                resumed_supervisor.identity.agent_id:
                    resumed_supervisor,
            },
            runtime_context=resumed_runtime_context,
        )
    )

    resumed_supervisor_context = restored_contexts[
        resumed_supervisor.identity.agent_id
    ]

    # ========================================================
    # 8. Verify AgentExecutionContext restoration
    # ========================================================

    assert (
        resumed_supervisor_context.runtime_context
        is resumed_runtime_context
    )

    assert (
        resumed_supervisor_context.agent_identity.agent_id
        == resumed_supervisor.identity.agent_id
    )

    # The Supervisor must continue from the previous loop
    # state rather than starting from step 0.
    assert (
        resumed_supervisor_context.loop.step_count
        == 2
    )

    # The ResearchAgent observation must still exist.
    assert (
        len(
            resumed_supervisor_context.loop.observation_history
        )
        == 1
    )

    # ========================================================
    # 9. Resume Supervisor
    # ========================================================
    #
    # IMPORTANT:
    #
    # We pass the restored AgentExecutionContext explicitly.
    #
    # AgentRuntime must NOT create a new context here.
    # ========================================================

    resumed_result = await agent_runtime.execute(
        agent=resumed_supervisor,
        task=task,
        runtime_context=resumed_runtime_context,
        agent_execution_context=(
            resumed_supervisor_context
        ),
    )

    # ========================================================
    # 10. Verify Resume result
    # ========================================================

    assert isinstance(
        resumed_result,
        AgentResult,
    )

    assert resumed_result.success is True

    # Supervisor should have selected "final".
    assert resumed_result.output is not None

    # The Supervisor continues from step 2 and therefore
    # executes step 3.
    assert (
        resumed_supervisor_context.loop.step_count
        == 3
    )

    # The original Research observation must remain.
    assert (
        len(
            resumed_supervisor_context.loop.observation_history
        )
        == 1
    )

    # ========================================================
    # 11. Most important assertion:
    #
    # ResearchAgent must NOT execute again.
    # ========================================================
    #
    # ResearchAgent was invoked once during the original
    # execution.
    #
    # During Resume, Supervisor directly selected "final".
    #
    # Therefore no second ResearchAgent invocation occurs.
    #
    # ResearchAgent's LLM provider has exactly two expected
    # calls:
    #
    #     market_research
    #     final
    #
    # If ResearchAgent were accidentally invoked again,
    # ResearchLLMProvider would receive a third call and fail.
    # ========================================================

    research_llm_provider = (
        research_agent._llm_provider
    )

    assert research_llm_provider.calls == 2

    # ========================================================
    # 12. SharedContext must remain available after Resume
    # ========================================================

    resumed_research_report = (
        resumed_runtime_context.shared_context.get(
            ResearchAgent.RESEARCH_REPORT_KEY
        )
    )

    assert resumed_research_report is not None

    assert (
        resumed_research_report
        == research_report
    )