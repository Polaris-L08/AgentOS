import pytest

from runtime.loop.loop_state import LoopState
from runtime.checkpoint import MemoryCheckpointStore, Checkpoint
from runtime.context import ContextState
from models.task_request import TaskRequest

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