from __future__ import annotations

from typing import Any

import pytest

from agents.agent_result import AgentResult
from agents.identity import AgentIdentity
from agents.research.domain.report import ResearchReport
from agents.research.domain.task import ResearchTask
from agents.research.research_agent import ResearchAgent
from models.task_request import TaskRequest
from providers.llm_provider import LLMProvider
from providers.llm_response import LLMResponse
from providers.prompt_message import PromptMessage
from runtime.context.context_state import ContextState
from runtime.events.event_bus import EventBus
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder
from tools.base import AbstractTool
from tools.registry import ToolRegistry
from tools.result import ToolResult
from tools.tool_executor import ToolExecutor


class MarketResearchTool(AbstractTool):
    """
    Test implementation of a domain research tool.

    This is not a MockTool.
    It represents a concrete Tool contract used by
    ResearchAgent.
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
            context_state: ContextState
    ) -> ToolResult:
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

class MockLLMProvider(LLMProvider):
    """
    Deterministic LLM provider for ResearchAgent integration tests.
    """
    async def generate(self, messages: list[PromptMessage]) -> LLMResponse:
        return LLMResponse(
            content="market_research",
            metadata={
                "model": "test-model",
            },
        )

class InvalidLLMProvider(LLMProvider):
    async def generate(self, messages: list[PromptMessage]) -> LLMResponse:
        return LLMResponse(
            content="dangerous_tool",
        )

class SequentialMockLLMProvider(LLMProvider):
    """
    LLM provider that returns a deterministic sequence
    of Agent decisions.
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
                content="market_research",
            )

        return LLMResponse(
            content="final",
        )

@pytest.mark.asyncio
async def test_research_agent_runtime_execution():
    # -------------------------------------------------
    # Tool
    # -------------------------------------------------
    registry = ToolRegistry()

    registry.register(MarketResearchTool())

    event_bus = EventBus()

    tool_executor = ToolExecutor(registry, event_bus)

    # -------------------------------------------------
    # Agent
    # -------------------------------------------------

    agent = ResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent-001",
            agent_type="investment_research",
            name="ResearchAgent",
        ),
        tool_executor=tool_executor,
        llm_provider=MockLLMProvider(),
    )

    # -------------------------------------------------
    # Runtime
    # -------------------------------------------------

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    runtime_context = execution_runtime.create_context()

    agent_runtime = AgentRuntime()

    # -------------------------------------------------
    # Runtime task
    # -------------------------------------------------

    task_request = TaskRequest(
        task_id="research-request-001",
        user_input="Analyze NVIDIA investment outlook.",
    )

    # -------------------------------------------------
    # Execute
    # -------------------------------------------------

    result = await agent_runtime.execute(
        agent=agent,
        task=task_request,
        runtime_context=runtime_context,
    )

    # -------------------------------------------------
    # Assertions
    # -------------------------------------------------

    assert isinstance(result, AgentResult)

    assert result.success is True

    assert isinstance(
        result.output,
        ResearchReport,
    )

    report = result.output

    assert report.task_id == "research-request-001"

    assert report.subject == "NVIDIA"

    assert report.findings == (
        "The research subject is NVIDIA.",
        "The research objective is: Evaluate the investment outlook.",
    )

    assert isinstance(result, AgentResult)

    assert result.success is True

    assert isinstance(
        result.output,
        ResearchReport,
    )

    assert len(result.observations) == 1

    tool_result = result.observations[0]

    assert tool_result.success is True

    assert tool_result.output["subject"] == "NVIDIA"

    assert result.output.subject == "NVIDIA"

@pytest.mark.asyncio
async def test_research_agent_selects_market_research_tool():
    # -------------------------------------------------
    # Tool
    # -------------------------------------------------
    registry = ToolRegistry()

    registry.register(MarketResearchTool())

    event_bus = EventBus()

    tool_executor = ToolExecutor(registry, event_bus)

    # -------------------------------------------------
    # Agent
    # -------------------------------------------------

    agent = ResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent-001",
            agent_type="investment_research",
            name="ResearchAgent",
        ),
        tool_executor=tool_executor,
        llm_provider=MockLLMProvider()
    )

    # -------------------------------------------------
    # Runtime
    # -------------------------------------------------

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    runtime_context = execution_runtime.create_context()

    agent_runtime = AgentRuntime()

    # -------------------------------------------------
    # Runtime task
    # -------------------------------------------------

    task_request = TaskRequest(
        task_id="research-request-002",
        user_input="Analyze NVIDIA stock valuation.",
    )

    # -------------------------------------------------
    # Execute
    # -------------------------------------------------

    result = await agent_runtime.execute(
        agent=agent,
        task=task_request,
        runtime_context=runtime_context,
    )

    # -------------------------------------------------
    # Assertions
    # -------------------------------------------------
    assert result.success is True

    assert result.output.subject == "NVIDIA"

    assert len(result.observations) == 1

    tool_result = result.observations[0]

    assert tool_result.success is True

@pytest.mark.asyncio
async def test_research_agent_rejects_unsupported_llm_tool():
    # -------------------------------------------------
    # Tool
    # -------------------------------------------------
    registry = ToolRegistry()

    registry.register(MarketResearchTool())

    event_bus = EventBus()

    tool_executor = ToolExecutor(registry, event_bus)

    # -------------------------------------------------
    # Agent
    # -------------------------------------------------

    agent = ResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent-001",
            agent_type="investment_research",
            name="ResearchAgent",
        ),
        tool_executor=tool_executor,
        llm_provider=InvalidLLMProvider()
    )

    # -------------------------------------------------
    # Runtime
    # -------------------------------------------------

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    runtime_context = execution_runtime.create_context()

    agent_runtime = AgentRuntime()

    # -------------------------------------------------
    # Execute
    # -------------------------------------------------
    with pytest.raises(ValueError, match="unsupported tool"):
        await agent_runtime.execute(
            agent=agent,
            task=TaskRequest(
                task_id="research-invalid-001",
                user_input="Analyze NVIDIA.",
            ),
            runtime_context=runtime_context,
        )
    # result = await agent_runtime.execute(
    #     agent=agent,
    #     task=TaskRequest(
    #         task_id="research-invalid-001",
    #         user_input="Analyze NVIDIA",
    #     ),
    #     runtime_context=runtime_context,
    # )

@pytest.mark.asyncio
async def test_research_agent_multi_round_execution():
    registry = ToolRegistry()

    registry.register(MarketResearchTool())

    event_bus = EventBus()

    tool_executor = ToolExecutor(registry, event_bus)

    llm_provider = SequentialMockLLMProvider()

    agent = ResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent-001",
            agent_type="investment_research",
            name="ResearchAgent",
        ),
        tool_executor=tool_executor,
        llm_provider=llm_provider,
    )

    # -------------------------------------------------
    # Runtime
    # -------------------------------------------------

    execution_runtime = ExecutionRuntime(
        trace_recorder=TraceRecorder()
    )

    runtime_context = execution_runtime.create_context()

    agent_runtime = AgentRuntime()

    result = await agent_runtime.execute(
        agent=agent,
        task=TaskRequest(
            task_id="research-multi-round-001",
            user_input="Analyze NVIDIA market valuation.",
        ),
        runtime_context=runtime_context,
    )

    assert result.success is True

    assert isinstance(
        result.output,
        ResearchReport,
    )

    assert llm_provider.calls == 2

    assert len(result.observations) == 1