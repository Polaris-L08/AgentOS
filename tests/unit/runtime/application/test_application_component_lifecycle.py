from __future__ import annotations

import pytest

from agents.agent_result import AgentResult
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from models.task_request import TaskRequest
from runtime.application import (
    AgentApplication,
    ApplicationAssembly,
    ApplicationComponent,
    ApplicationState,
)
from runtime.application.application_config import ApplicationConfig
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
)
from runtime.execution.agent_runtime import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.tracing.trace_recorder import TraceRecorder


class MockAgent(BaseAgent):
    async def run(
        self,
        task,
        agent_execution_context,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            output=task.user_input,
        )


class RecordingComponent:
    """
    Test Application Component.

    Records lifecycle calls and can optionally fail at one lifecycle
    phase.
    """

    def __init__(
        self,
        name: str,
        calls: list[str],
        fail_on: str | None = None,
    ) -> None:
        self.name = name
        self.calls = calls
        self.fail_on = fail_on

    async def initialize(self) -> None:
        self.calls.append(
            f"{self.name}.initialize"
        )

        if self.fail_on == "initialize":
            raise RuntimeError(
                f"{self.name} initialize failed"
            )

    async def start(self) -> None:
        self.calls.append(
            f"{self.name}.start"
        )

        if self.fail_on == "start":
            raise RuntimeError(
                f"{self.name} start failed"
            )

    async def stop(self) -> None:
        self.calls.append(
            f"{self.name}.stop"
        )

        if self.fail_on == "stop":
            raise RuntimeError(
                f"{self.name} stop failed"
            )


def create_application(
    *components: tuple[str, object],
) -> AgentApplication:
    assembly = ApplicationAssembly(
        ApplicationConfig(
            application_id="app-1",
            name="Test Application",
        )
    )

    assembly.register_component(
        "agent_runtime",
        AgentRuntime(),
    )

    assembly.register_component(
        "execution_runtime",
        ExecutionRuntime(
            trace_recorder=TraceRecorder(),
        ),
    )

    for name, component in components:
        assembly.register_component(
            name,
            component,
        )

    assembly.add_agent(
        MockAgent(
            identity=AgentIdentity(
                agent_id="agent-1",
                agent_type="mock",
                name="Mock Agent",
            )
        )
    )

    return assembly.build()


def test_application_component_protocol_describes_lifecycle_contract():
    component = RecordingComponent(
        "component",
        [],
    )

    assert isinstance(
        component,
        ApplicationComponent,
    )


@pytest.mark.asyncio
async def test_initialize_orchestrates_components_in_registration_order():
    calls: list[str] = []

    first = RecordingComponent(
        "first",
        calls,
    )

    second = RecordingComponent(
        "second",
        calls,
    )

    application = create_application(
        ("first", first),
        ("second", second),
    )

    await application.initialize()

    assert application.state is ApplicationState.INITIALIZED

    assert calls == [
        "first.initialize",
        "second.initialize",
    ]


@pytest.mark.asyncio
async def test_start_orchestrates_initialized_components_in_registration_order():
    calls: list[str] = []

    first = RecordingComponent(
        "first",
        calls,
    )

    second = RecordingComponent(
        "second",
        calls,
    )

    application = create_application(
        ("first", first),
        ("second", second),
    )

    await application.initialize()
    await application.start()

    assert application.state is ApplicationState.RUNNING

    assert calls == [
        "first.initialize",
        "second.initialize",
        "first.start",
        "second.start",
    ]


@pytest.mark.asyncio
async def test_stop_orchestrates_components_in_reverse_order():
    calls: list[str] = []

    first = RecordingComponent(
        "first",
        calls,
    )

    second = RecordingComponent(
        "second",
        calls,
    )

    application = create_application(
        ("first", first),
        ("second", second),
    )

    await application.initialize()
    await application.start()
    await application.stop()

    assert application.state is ApplicationState.STOPPED

    assert calls == [
        "first.initialize",
        "second.initialize",
        "first.start",
        "second.start",
        "second.stop",
        "first.stop",
    ]


@pytest.mark.asyncio
async def test_non_lifecycle_component_is_not_touched():
    calls: list[str] = []

    class PlainComponent:
        pass

    lifecycle_component = RecordingComponent(
        "lifecycle",
        calls,
    )

    plain_component = PlainComponent()

    application = create_application(
        ("plain", plain_component),
        ("lifecycle", lifecycle_component),
    )

    await application.initialize()
    await application.start()
    await application.stop()

    assert calls == [
        "lifecycle.initialize",
        "lifecycle.start",
        "lifecycle.stop",
    ]


@pytest.mark.asyncio
async def test_initialize_failure_rolls_back_successfully_initialized_components():
    calls: list[str] = []

    first = RecordingComponent(
        "first",
        calls,
    )

    second = RecordingComponent(
        "second",
        calls,
        fail_on="initialize",
    )

    application = create_application(
        ("first", first),
        ("second", second),
    )

    with pytest.raises(
        RuntimeError,
        match="second initialize failed",
    ):
        await application.initialize()

    assert application.state is ApplicationState.CREATED

    assert calls == [
        "first.initialize",
        "second.initialize",
        "first.stop",
    ]


@pytest.mark.asyncio
async def test_start_failure_rolls_back_successfully_started_components():
    calls: list[str] = []

    first = RecordingComponent(
        "first",
        calls,
    )

    second = RecordingComponent(
        "second",
        calls,
        fail_on="start",
    )

    application = create_application(
        ("first", first),
        ("second", second),
    )

    await application.initialize()

    with pytest.raises(
        RuntimeError,
        match="second start failed",
    ):
        await application.start()

    assert application.state is ApplicationState.INITIALIZED

    assert calls == [
        "first.initialize",
        "second.initialize",
        "first.start",
        "second.start",
        "first.stop",
    ]

    # Startup can be retried without reinitializing the Application.
    second.fail_on = None

    await application.start()

    assert application.state is ApplicationState.RUNNING

    await application.stop()


@pytest.mark.asyncio
async def test_stop_failure_leaves_application_in_stopping_state():
    calls: list[str] = []

    component = RecordingComponent(
        "component",
        calls,
        fail_on="stop",
    )

    application = create_application(
        ("component", component),
    )

    await application.initialize()
    await application.start()

    with pytest.raises(
        RuntimeError,
        match="component stop failed",
    ):
        await application.stop()

    assert application.state is ApplicationState.STOPPING


@pytest.mark.asyncio
async def test_application_owns_component_snapshot_from_assembly():
    calls: list[str] = []

    component = RecordingComponent(
        "component",
        calls,
    )

    assembly = ApplicationAssembly(
        ApplicationConfig(
            application_id="app-1",
            name="Test Application",
        )
    )

    assembly.register_component(
        "agent_runtime",
        AgentRuntime(),
    )

    assembly.register_component(
        "execution_runtime",
        ExecutionRuntime(
            trace_recorder=TraceRecorder(),
        ),
    )

    assembly.register_component(
        "component",
        component,
    )

    assembly.add_agent(
        MockAgent(
            identity=AgentIdentity(
                agent_id="agent-1",
                agent_type="mock",
                name="Mock Agent",
            )
        )
    )

    application = assembly.build()

    # Application owns a snapshot. Changes to the Assembly after build
    # must not change the running Application's lifecycle components.
    extra = RecordingComponent(
        "extra",
        calls,
    )

    assembly.register_component(
        "extra",
        extra,
    )

    await application.initialize()
    await application.start()
    await application.stop()

    assert "extra.initialize" not in calls
    assert "extra.start" not in calls
    assert "extra.stop" not in calls


@pytest.mark.asyncio
async def test_application_lifecycle_remains_unchanged_without_lifecycle_components():
    application = create_application()

    await application.initialize()
    await application.start()
    await application.stop()

    assert application.state is ApplicationState.STOPPED


@pytest.mark.asyncio
async def test_invalid_lifecycle_transition_is_still_rejected():
    application = create_application()

    with pytest.raises(ApplicationLifecycleError):
        await application.start()