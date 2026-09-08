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
from runtime.application.application import AgentApplication
from runtime.checkpoint.checkpoint_coordinator import (
    CheckpointCoordinator,
)
from runtime.checkpoint.memory_checkpoint_store import (
    MemoryCheckpointStore,
)
from runtime.context.agent_execution_context import (
    AgentExecutionContext,
)
from runtime.events.event_bus import EventBus
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import (
    ExecutionRuntime,
)
from runtime.loop.loop_state import LoopState
from runtime.tracing.trace_recorder import TraceRecorder
from tools.base import AbstractTool
from tools.registry import ToolRegistry
from tools.result import ToolResult
from tools.tool_executor import ToolExecutor


# ============================================================
# Test Tool
# ============================================================


class MarketResearchTool(AbstractTool):
    """
    Deterministic Tool used by ResearchAgent.
    """

    @property
    def name(self) -> str:
        return "market_research"

    @property
    def description(self) -> str:
        return "Retrieve market research data."

    async def execute(
        self,
        input: Any,
        context_state,
    ) -> ToolResult:

        return ToolResult(
            success=True,
            output={
                "subject": input["subject"],
                "objective": input["objective"],
                "market_data": (
                    f"Research data for "
                    f"{input['subject']}."
                ),
            },
            metadata={
                "source": "test_market_data_provider",
            },
        )


# ============================================================
# Deterministic LLM Providers
# ============================================================


class ResearchLLMProvider(LLMProvider):
    """
    ResearchAgent LLM provider.

    ResearchAgent performs:

        market_research
        final
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
            "ResearchLLMProvider received "
            "an unexpected additional call."
        )


class CrashSupervisorLLMProvider(LLMProvider):
    """
    Supervisor provider used before the simulated crash.

    Expected:

        call 1 -> research
        call 2 -> crash
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
            "Simulated process crash "
            "after ResearchAgent."
        )


class ResumeSupervisorLLMProvider(LLMProvider):
    """
    Supervisor provider used after recovery.

    The ResearchAgent result is already available.

    Therefore Supervisor should return:

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
# Inspectable Supervisor
# ============================================================


class InspectableSupervisorAgent(
    SupervisorAgent
):
    """
    Test-only Supervisor subclass.

    It records the AgentExecutionContext supplied by
    AgentRuntime.

    Production SupervisorAgent remains unchanged.
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

        self.execution_context = None

    async def run(
        self,
        task: TaskRequest,
        agent_execution_context: AgentExecutionContext,
    ) -> AgentResult:

        self.execution_context = (
            agent_execution_context
        )

        return await super().run(
            task,
            agent_execution_context,
        )


# ============================================================
# Helpers
# ============================================================


def create_research_agent(
    agent_runtime: AgentRuntime,
) -> ResearchAgent:

    registry = ToolRegistry()

    registry.register(
        MarketResearchTool()
    )

    tool_executor = ToolExecutor(
        registry=registry,
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
    return TaskRequest(
        task_id="task-resume-001",
        user_input="Analyze NVIDIA stock",
    )


# ============================================================
# End-to-End Recovery Test
# ============================================================


@pytest.mark.asyncio
async def test_application_can_resume_supervisor_from_checkpoint():
    """
    Verify the complete Application-level recovery flow.

    Original execution:

        Application
            ↓
        Supervisor
            ↓
        ResearchAgent
            ↓
        Research result
            ↓
        SharedContext
            ↓
        Supervisor LoopState
            ↓
        Checkpoint
            ↓
        simulated crash

    Recovery:

        Checkpoint
            ↓
        ApplicationExecutor
            ↓
        ExecutionRuntime.resume_execution()
            ↓
        ExecutionHandle
            ↓
        RuntimeContext
            ↓
        restore Supervisor AgentExecutionContext
            ↓
        AgentRuntime
            ↓
        Supervisor
            ↓
        final

    Most important acceptance criterion:

        ResearchAgent must NOT execute again.
    """

    # ---------------------------------------------------------
    # Runtime
    # ---------------------------------------------------------

    agent_runtime = AgentRuntime()

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    # ---------------------------------------------------------
    # Research Agent
    # ---------------------------------------------------------

    research_agent = create_research_agent(
        agent_runtime
    )

    # ---------------------------------------------------------
    # First Supervisor
    # ---------------------------------------------------------

    first_supervisor = (
        InspectableSupervisorAgent(
            identity=AgentIdentity(
                agent_id="supervisor-agent-001",
                agent_type="supervisor",
                name="SupervisorAgent",
            ),
            agent_runtime=agent_runtime,
            research_agent=research_agent,
            llm_provider=(
                CrashSupervisorLLMProvider()
            ),
        )
    )

    # ---------------------------------------------------------
    # First Application
    # ---------------------------------------------------------

    application = AgentApplication(
        application_id="app-001",
        name="Test Investment Application",
        agent_runtime=agent_runtime,
        execution_runtime=execution_runtime,
        agents=[
            first_supervisor,
            research_agent,
        ],
    )

    executor = application._executor

    task = create_task()

    # ---------------------------------------------------------
    # Start first execution
    # ---------------------------------------------------------

    execution = (
        execution_runtime.create_execution()
    )

    try:
        with pytest.raises(
            RuntimeError,
            match="Simulated process crash",
        ):
            await agent_runtime.execute(
                agent=first_supervisor,
                task=task,
                runtime_context=(
                    execution.runtime_context
                ),
            )

        # -----------------------------------------------------
        # Verify pre-crash state
        # -----------------------------------------------------

        assert (
            first_supervisor.execution_context
            is not None
        )

        supervisor_context = (
            first_supervisor.execution_context
        )

        assert (
            supervisor_context.loop.step_count
            == 2
        )

        assert (
            len(
                supervisor_context
                .loop
                .observation_history
            )
            == 1
        )

        # ResearchAgent completed once.
        assert (
            research_agent
            ._llm_provider
            .calls
            == 2
        )

        research_report = (
            execution
            .runtime_context
            .shared_context
            .get(
                ResearchAgent.RESEARCH_REPORT_KEY
            )
        )

        assert research_report is not None

        # -----------------------------------------------------
        # Create checkpoint
        # -----------------------------------------------------

        checkpoint_coordinator = (
            CheckpointCoordinator()
        )

        checkpoint = (
            checkpoint_coordinator
            .create_checkpoint(
                runtime_context=(
                    execution.runtime_context
                ),
                agent_execution_contexts={
                    first_supervisor.identity.agent_id:
                        supervisor_context,
                },
                task_id=task.task_id,
            )
        )

    finally:
        await execution.close()

    # ---------------------------------------------------------
    # Persist checkpoint
    # ---------------------------------------------------------

    checkpoint_store = MemoryCheckpointStore()

    await checkpoint_store.save(
        checkpoint.checkpoint_id,
        checkpoint,
    )

    restored_checkpoint = (
        await checkpoint_store.load(
            checkpoint.checkpoint_id
        )
    )

    assert restored_checkpoint is not None

    # ---------------------------------------------------------
    # Simulate a new process / Application instance
    # ---------------------------------------------------------
    #
    # The new Application owns a new Supervisor instance.
    #
    # The ResearchAgent instance is deliberately reused here
    # only as an existing Application capability.
    #
    # Its previous execution result is represented by the
    # Checkpoint and SharedContext.
    # ---------------------------------------------------------

    resumed_supervisor = (
        InspectableSupervisorAgent(
            identity=AgentIdentity(
                agent_id="supervisor-agent-001",
                agent_type="supervisor",
                name="SupervisorAgent",
            ),
            agent_runtime=agent_runtime,
            research_agent=research_agent,
            llm_provider=(
                ResumeSupervisorLLMProvider()
            ),
        )
    )

    resumed_application = AgentApplication(
        application_id="app-001",
        name="Test Investment Application",
        agent_runtime=agent_runtime,
        execution_runtime=ExecutionRuntime(
            trace_recorder=TraceRecorder()
        ),
        agents=[
            resumed_supervisor,
            research_agent,
        ],
    )

    resumed_executor = (
        resumed_application._executor
    )

    # ---------------------------------------------------------
    # Recovery
    # ---------------------------------------------------------

    result = (
        await resumed_executor
        .recover_agent_execution(
            checkpoint=restored_checkpoint,
            agent_id=(
                resumed_supervisor
                .identity
                .agent_id
            ),
            task=task,
        )
    )

    # ---------------------------------------------------------
    # Verify final result
    # ---------------------------------------------------------

    assert result.success is True

    assert result.output is not None

    # ---------------------------------------------------------
    # Verify restored Supervisor state
    # ---------------------------------------------------------

    assert (
        resumed_supervisor.execution_context
        is not None
    )

    assert (
            resumed_supervisor.execution_context
            is not first_supervisor.execution_context
    )

    assert (
            resumed_supervisor.execution_context.agent_context
            is resumed_supervisor.context
    )

    assert (
            resumed_supervisor.execution_context.memory
            is resumed_supervisor.memory
    )

    resumed_context = (
        resumed_supervisor.execution_context
    )

    # Checkpoint had step_count == 2.
    #
    # Supervisor continues and executes one more
    # decision step.
    assert (
        resumed_context.loop.step_count
        == 3
    )

    # Existing Research observation remains.
    assert (
        len(
            resumed_context
            .loop
            .observation_history
        )
        == 1
    )

    # ---------------------------------------------------------
    # Verify SharedContext survived recovery
    # ---------------------------------------------------------

    recovered_report = (
        resumed_context
        .runtime_context
        .shared_context
        .get(
            ResearchAgent.RESEARCH_REPORT_KEY
        )
    )

    assert recovered_report is not None

    # assert (
    #     recovered_report
    #     == research_report
    # )

    # ---------------------------------------------------------
    # MOST IMPORTANT ASSERTION
    # ---------------------------------------------------------
    #
    # ResearchAgent already executed:
    #
    #     market_research
    #     final
    #
    # It must NOT execute again after Supervisor recovery.
    #
    # If Supervisor accidentally selects ResearchAgent again,
    # ResearchLLMProvider will receive a third call and raise.
    # ---------------------------------------------------------

    assert (
        research_agent
        ._llm_provider
        .calls
        == 2
    )

    # The resumed Supervisor made exactly one decision.
    assert (
        resumed_supervisor
        ._llm_provider
        .calls
        == 1
    )