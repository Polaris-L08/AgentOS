from __future__ import annotations

import pytest

from actions.observation import Observation
from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from runtime.checkpoint.checkpoint import (
    AgentCheckpoint,
    Checkpoint,
)
from runtime.context.context_state import ContextState
from runtime.context.shared_context import SharedContext
from runtime.loop.loop_state import LoopState

@pytest.mark.asyncio
def test_checkpoint_serialization_roundtrip():

    checkpoint = Checkpoint(
        runtime_id="runtime-001",
        shared_context=SharedContext(
            data={
                "research.status": "completed",
                "research.score": 95,
            }
        ),
        agents={
            "research-agent": AgentCheckpoint(
                agent_id="research-agent",
                state=ContextState(),
                loop=LoopState(
                    step_count=3,
                    observation_history=[
                        Observation(
                            success=True,
                            content="Research completed.",
                        )
                    ],
                ),
            )
        },
        task_id="task-001",
    )

    data = checkpoint.model_dump()

    restored = Checkpoint.model_validate(data)

    assert restored.runtime_id == "runtime-001"

    assert restored.task_id == "task-001"

    assert (
        restored.shared_context.data["research.status"]
        == "completed"
    )

    assert (
        restored.shared_context.data["research.score"]
        == 95
    )

    assert (
        restored.agents["research-agent"]
        .loop.step_count
        == 3
    )

    assert (
        restored.agents["research-agent"]
        .loop.observation_history[0]
        .content
        == "Research completed."
    )

@pytest.mark.asyncio
def test_checkpoint_json_roundtrip():

    checkpoint = Checkpoint(
        runtime_id="runtime-002",
        shared_context=SharedContext(
            data={
                "research.status": "running",
            }
        ),
        agents={
            "research-agent": AgentCheckpoint(
                agent_id="research-agent",
                state=ContextState(),
                loop=LoopState(
                    step_count=2,
                ),
            )
        },
        task_id="task-002",
    )

    payload = checkpoint.model_dump_json()

    restored = Checkpoint.model_validate_json(payload)

    assert restored.runtime_id == "runtime-002"

    assert restored.task_id == "task-002"

    assert (
        restored.shared_context.data["research.status"]
        == "running"
    )

    assert (
        restored.agents["research-agent"]
        .loop.step_count
        == 2
    )

# import pytest
#
# from runtime.checkpoint.checkpoint_coordinator import (
#     CheckpointCoordinator,
# )
from runtime.checkpoint.memory_checkpoint_store import (
    MemoryCheckpointStore,
)
from runtime.context.shared_context import SharedContext
from runtime.context.context_state import ContextState
from runtime.checkpoint.checkpoint import (
    AgentCheckpoint,
    Checkpoint,
)
from runtime.loop.loop_state import LoopState


@pytest.mark.asyncio
async def test_checkpoint_store_roundtrip():

    store = MemoryCheckpointStore()

    checkpoint = Checkpoint(
        runtime_id="runtime-003",
        shared_context=SharedContext(
            data={
                "status": "running",
            }
        ),
        agents={
            "research-agent": AgentCheckpoint(
                agent_id="research-agent",
                state=ContextState(),
                loop=LoopState(
                    step_count=4,
                ),
            )
        },
        task_id="task-003",
    )

    await store.save(
        "checkpoint-001",
        checkpoint,
    )

    restored = await store.load(
        "checkpoint-001"
    )

    assert restored is not None

    assert restored.runtime_id == "runtime-003"

    assert (
        restored.shared_context.data["status"]
        == "running"
    )

    assert (
        restored.agents["research-agent"]
        .loop.step_count
        == 4
    )