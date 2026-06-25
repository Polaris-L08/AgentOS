from checkpoint.checkpoint import Checkpoint
from checkpoint.checkpoint_store import CheckpointStore


class MemoryCheckpointStore(CheckpointStore):

    def __init__(self):
        self._storage: dict[str, Checkpoint] = {}

    async def save(self, checkpoint_id: str, checkpoint: Checkpoint) -> None:
        self._storage[checkpoint_id] = checkpoint

    async def load(self, checkpoint_id: str) -> Checkpoint | None:
        return self._storage.get(checkpoint_id)

    async def delete(self, checkpoint_id: str) -> None:
        self._storage.pop(checkpoint_id, None)