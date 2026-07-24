from __future__ import annotations

import pytest

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from agents.result import AgentResult
from models.task_request import TaskRequest
from runtime.context.runtime_context import RuntimeContext
from runtime.events.event import Event
from runtime.events.publisher import EventPublisher
from runtime.execution.agent_runtime import AgentRuntime
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.middleware.tracing_middleware import TracingMiddleware
from tests.conftest import runtime_context, event_bus
from tests.event.recording_subscriber import RecordingSubscriber


class MockAgent(BaseAgent):
    """
    Mock agent for AgentRuntime event testing.
    """
    async def run(
        self,
        task,
        runtime_context: RuntimeContext
    ) -> AgentResult:

        return AgentResult(
            success=True,
            output="success"
        )


@pytest.mark.asyncio
async def test_agent_runtime_publish_events(
        runtime_context,
        event_bus
):

    subscriber = RecordingSubscriber()

    event_bus.subscribe(
        event_type="agent.started",
        subscriber=subscriber
    )
    event_bus.subscribe(
        event_type="agent.completed",
        subscriber=subscriber
    )


    runtime = AgentRuntime(
        publisher=event_bus
    )
    # middleware_chain = MiddlewareChain(
    #     [
    #         TracingMiddleware()
    #     ]
    # )
    # runtime = AgentRuntime(middleware_chain)

    agent = MockAgent(
        AgentIdentity(
            agent_id="mock-agent-001",
            agent_type="test",
            name="MockAgent"
        )
    )

    task = TaskRequest(task_id="1", user_input="test")

    result = await runtime.execute(
        agent=agent,
        task=task,
        runtime_context=runtime_context
    )


    assert result.success is True

    assert len(subscriber.events) == 2

    event_types = [
        event.type
        for event in subscriber.events
    ]

    assert "agent.started" in event_types

    assert "agent.completed" in event_types

    started_event = next(
        event
        for event in subscriber.events
        if event.type == "agent.started"
    )

    assert started_event.source == "agent_runtime"

    assert started_event.receiver == "MockAgent"

    assert started_event.payload["agent_id"] == "mock-agent-001"