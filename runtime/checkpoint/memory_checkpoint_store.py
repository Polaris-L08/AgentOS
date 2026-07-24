from runtime.checkpoint.checkpoint import Checkpoint
from runtime.checkpoint.checkpoint_store import CheckpointStore


class MemoryCheckpointStore(CheckpointStore):

    def __init__(self):
        self._storage: dict[str, dict] = {}

    async def save(self, checkpoint_id: str, checkpoint: Checkpoint) -> None:
        self._storage[checkpoint_id] = checkpoint.model_dump()

    async def load(self, checkpoint_id: str) -> Checkpoint | None:
        data = self._storage.get(checkpoint_id)

        if data is None:
            return None

        return Checkpoint.model_validate(data)

    async def delete(self, checkpoint_id: str) -> None:
        self._storage.pop(checkpoint_id, None)