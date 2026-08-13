from typing import Any

import pytest

from agents.identity import AgentIdentity
from agents.research.research_agent import ResearchAgent
from agents.supervisor_agent import SupervisorAgent
from models.task_request import TaskRequest
from providers.llm_provider import LLMProvider
from providers.llm_response import LLMResponse
from providers.prompt_message import PromptMessage
from runtime.context.context_state import ContextState
from runtime.events.event_bus import EventBus
from runtime.execution import AgentRuntime
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

class MockLLMProvider(LLMProvider):

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._index = 0

    async def generate(
        self,
        messages: list[PromptMessage],
    ) -> LLMResponse:

        if self._index >= len(self._responses):
            raise RuntimeError(
                "MockLLMProvider has no more responses."
            )

        content = self._responses[self._index]

        self._index += 1

        return LLMResponse(
            content=content
        )

@pytest.mark.asyncio
async def test_supervisor_agent():
    task = TaskRequest(
        task_id="research-request-001",
        user_input="Analyze NVIDIA stock"
    )

    agent_runtime = AgentRuntime()

    runtime_context = ExecutionRuntime(TraceRecorder()).create_context()

    registry = ToolRegistry()

    registry.register(MarketResearchTool())

    event_bus = EventBus()

    tool_executor = ToolExecutor(registry, event_bus)

    research_agent = ResearchAgent(
        identity=AgentIdentity(
            agent_id="research-agent-001",
            agent_type="investment_research",
            name="ResearchAgent",
        ),
        tool_executor=tool_executor,
        llm_provider=MockLLMProvider(
            responses=[
                "market_research",
                "final",
            ]
        ),
    )

    supervisor_agent = SupervisorAgent(
        identity=AgentIdentity(
            agent_id="supervisor-agent-001",
            agent_type="supervisor",
            name="SupervisorAgent",
        ),
        agent_runtime=agent_runtime,
        research_agent=research_agent,
        llm_provider=MockLLMProvider(
            responses=[
                "research",
                "research",
                "final",
            ])
    )

    # run
    result = await agent_runtime.execute(
        agent=supervisor_agent,
        task=task,
        runtime_context=runtime_context,
    )

    print(result)