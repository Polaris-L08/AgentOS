from __future__ import annotations

import pytest

from actions.observation import Observation
from runtime.checkpoint import Checkpoint
from runtime.checkpoint.checkpoint import AgentCheckpoint
from runtime.context.context_state import ContextState
from runtime.context.shared_context import SharedContext
from runtime.loop.loop_state import LoopState
from runtime.persistence import PostgresCheckpointStore


@pytest.fixture
def checkpoint_store(postgres_database):
    return PostgresCheckpointStore(postgres_database)


def create_checkpoint(
    checkpoint_id: str,
    runtime_id: str = "runtime-integration-001",
    task_id: str | None = "task-integration-001",
) -> Checkpoint:
    return Checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id=runtime_id,
        shared_context=SharedContext(
            data={
                "research.status": "completed",
                "research.score": 95,
            },
        ),
        agents={
            "research-agent": AgentCheckpoint(
                agent_id="research-agent",
                status="COMPLETED",
                state=ContextState(),
                loop=LoopState(
                    step_count=3,
                    observation_history=[
                        Observation(
                            success=True,
                            content="Research completed.",
                        ),
                    ],
                ),
            ),
        },
        task_id=task_id,
    )


@pytest.mark.asyncio
async def test_save_and_load_checkpoint(
    checkpoint_store: PostgresCheckpointStore,
) -> None:
    checkpoint = create_checkpoint(
        checkpoint_id="checkpoint-integration-001",
    )

    await checkpoint_store.save(
        checkpoint.checkpoint_id,
        checkpoint,
    )

    loaded = await checkpoint_store.load(
        checkpoint.checkpoint_id,
    )

    assert loaded is not None

    assert loaded.checkpoint_id == checkpoint.checkpoint_id
    assert loaded.runtime_id == checkpoint.runtime_id
    assert loaded.task_id == checkpoint.task_id

    assert (
        loaded.shared_context.data["research.status"]
        == "completed"
    )

    assert (
        loaded.shared_context.data["research.score"]
        == 95
    )

    assert (
        loaded.agents["research-agent"]
        .agent_id
        == "research-agent"
    )

    assert (
        loaded.agents["research-agent"]
        .status
        == "COMPLETED"
    )

    assert (
        loaded.agents["research-agent"]
        .loop.step_count
        == 3
    )

    assert (
        loaded.agents["research-agent"]
        .loop.observation_history[0]
        .content
        == "Research completed."
    )


@pytest.mark.asyncio
async def test_load_missing_checkpoint_returns_none(
    checkpoint_store: PostgresCheckpointStore,
) -> None:
    loaded = await checkpoint_store.load(
        "checkpoint-does-not-exist",
    )

    assert loaded is None


@pytest.mark.asyncio
async def test_save_replaces_existing_checkpoint(
    checkpoint_store: PostgresCheckpointStore,
) -> None:
    checkpoint_id = "checkpoint-integration-replace"

    first = create_checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id="runtime-first",
    )

    second = create_checkpoint(
        checkpoint_id=checkpoint_id,
        runtime_id="runtime-second",
    )

    second.shared_context.data["research.status"] = "running"
    second.shared_context.data["research.score"] = 70
    second.agents["research-agent"].loop.step_count = 8

    await checkpoint_store.save(
        checkpoint_id,
        first,
    )

    await checkpoint_store.save(
        checkpoint_id,
        second,
    )

    loaded = await checkpoint_store.load(
        checkpoint_id,
    )

    assert loaded is not None

    assert loaded.checkpoint_id == checkpoint_id
    assert loaded.runtime_id == "runtime-second"

    assert (
        loaded.shared_context.data["research.status"]
        == "running"
    )

    assert (
        loaded.shared_context.data["research.score"]
        == 70
    )

    assert (
        loaded.agents["research-agent"]
        .loop.step_count
        == 8
    )


@pytest.mark.asyncio
async def test_delete_checkpoint(
    checkpoint_store: PostgresCheckpointStore,
) -> None:
    checkpoint = create_checkpoint(
        checkpoint_id="checkpoint-integration-delete",
    )

    await checkpoint_store.save(
        checkpoint.checkpoint_id,
        checkpoint,
    )

    assert (
        await checkpoint_store.load(
            checkpoint.checkpoint_id,
        )
        is not None
    )

    await checkpoint_store.delete(
        checkpoint.checkpoint_id,
    )

    assert (
        await checkpoint_store.load(
            checkpoint.checkpoint_id,
        )
        is None
    )


@pytest.mark.asyncio
async def test_delete_missing_checkpoint_is_safe(
    checkpoint_store: PostgresCheckpointStore,
) -> None:
    await checkpoint_store.delete(
        "checkpoint-delete-missing",
    )

    assert (
        await checkpoint_store.load(
            "checkpoint-delete-missing",
        )
        is None
    )


@pytest.mark.asyncio
async def test_checkpoint_state_is_persisted_independently(
    checkpoint_store: PostgresCheckpointStore,
) -> None:
    checkpoint = create_checkpoint(
        checkpoint_id="checkpoint-integration-independent",
    )

    await checkpoint_store.save(
        checkpoint.checkpoint_id,
        checkpoint,
    )

    checkpoint.runtime_id = "runtime-modified"
    checkpoint.shared_context.data["research.status"] = "modified"
    checkpoint.agents["research-agent"].loop.step_count = 99

    loaded = await checkpoint_store.load(
        checkpoint.checkpoint_id,
    )

    assert loaded is not None

    assert loaded.runtime_id == "runtime-integration-001"

    assert (
        loaded.shared_context.data["research.status"]
        == "completed"
    )

    assert (
        loaded.agents["research-agent"]
        .loop.step_count
        == 3
    )