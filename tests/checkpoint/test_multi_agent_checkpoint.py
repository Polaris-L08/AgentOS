import pytest

from agents.identity import AgentIdentity

from runtime.checkpoint.checkpoint import Checkpoint
from runtime.checkpoint.memory_checkpoint_store import (
    MemoryCheckpointStore,
)

from runtime.context.agent_execution_context import (
    AgentExecutionContext,
)

from runtime.context.shared_context import SharedContext
from runtime.context.context_state import ContextState

from runtime.execution.execution_runtime import ExecutionRuntime

from runtime.loop.loop_state import LoopState

from runtime.tracing.trace_recorder import TraceRecorder



def create_agent_identity(
        agent_id: str
) -> AgentIdentity:

    return AgentIdentity(
        agent_id=agent_id,
        agent_type="test",
        name=agent_id
    )


def test_multi_agent_context_isolation():

    """
    Verify:
        Agent A
        Agent B

    share RuntimeContext
    but isolate:
        ContextState
        LoopState
    """

    execution_runtime = ExecutionRuntime(trace_recorder=TraceRecorder())

    runtime_context = execution_runtime.create_context()

    agent_a = AgentExecutionContext.create(
        runtime_context,
        create_agent_identity("agent_a")
    )

    agent_b = AgentExecutionContext.create(
        runtime_context,
        create_agent_identity("agent_b")
    )

    #
    # RuntimeContext shared
    #

    assert (agent_a.runtime_context is agent_b.runtime_context)

    #
    # Agent state isolated
    #

    agent_a.state.agent_context.variable_state.variables["key"] = "agent_a"

    assert (agent_b.state.agent_context.variable_state.variables.get("key")is None)

    #
    # Loop isolated
    #

    agent_a.loop.step_count = 10

    assert (agent_b.loop.step_count == 0)

@pytest.mark.asyncio
async def test_multi_agent_checkpoint_save_and_load():

    """
    Verify:
        AgentExecutionContext
                |
        Checkpoint
                |
        CheckpointStore

    serialization round trip.
    """

    store = MemoryCheckpointStore()

    checkpoint = Checkpoint(
        checkpoint_id="checkpoint001",
        runtime_id="runtime001",
        task_id="task001",
        shared_context=SharedContext(
            data={
                "request":
                    "multi agent test"
            }
        ),
        agents={}
    )

    checkpoint.agents["research"] = {
        "agent_id":
            "research",
        "state":
            ContextState(),
        "loop":
            LoopState()
    }

    await store.save(checkpoint.checkpoint_id, checkpoint)

    restored = await store.load(checkpoint.checkpoint_id)

    assert restored is not None

    assert (restored.runtime_id == "runtime001")

    assert (restored.task_id == "task001")

    assert (restored.shared_context.data["request"] == "multi agent test")