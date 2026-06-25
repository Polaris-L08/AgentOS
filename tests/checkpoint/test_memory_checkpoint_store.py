import pytest

from agents.loop_state import LoopState
from checkpoint import MemoryCheckpointStore, Checkpoint
from context.context_state import ContextState
from core.task_request import TaskRequest

@pytest.mark.asyncio
async def test_save_and_load_checkpoint():

    store = MemoryCheckpointStore()

    checkpoint = Checkpoint(
        task_request=TaskRequest(
            task_id="task-1",
            user_input="hello",
        ),
        loop_state=LoopState(),
        context_state=ContextState(),
    )

    await store.save(
        checkpoint_id="cp-1",
        checkpoint=checkpoint,
    )

    loaded = await store.load("cp-1")

    assert loaded is not None

    assert loaded.task_request.task_id == "task-1"