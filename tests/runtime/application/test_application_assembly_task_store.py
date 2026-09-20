from runtime.application.application_assembly import ApplicationAssembly
from runtime.application.application_config import ApplicationConfig
from runtime.persistence import InMemoryTaskStore


class FakeAgentRuntime:
    pass


class FakeExecutionRuntime:
    pass


def test_application_assembly_creates_default_task_store():
    assembly = ApplicationAssembly(
        config=ApplicationConfig(
            application_id="application-1",
            name="Task Store Test",
        )
    )

    assembly.register_component(
        "agent_runtime",
        FakeAgentRuntime(),
    )
    assembly.register_component(
        "execution_runtime",
        FakeExecutionRuntime(),
    )

    application = assembly.build()

    assert isinstance(
        application.task_store,
        InMemoryTaskStore,
    )


def test_application_assembly_accepts_explicit_task_store():
    task_store = InMemoryTaskStore()

    assembly = ApplicationAssembly(
        config=ApplicationConfig(
            application_id="application-1",
            name="Task Store Test",
        )
    )

    assembly.register_component(
        "agent_runtime",
        FakeAgentRuntime(),
    )
    assembly.register_component(
        "execution_runtime",
        FakeExecutionRuntime(),
    )
    assembly.register_component(
        "task_store",
        task_store,
    )

    application = assembly.build()

    assert application.task_store is task_store