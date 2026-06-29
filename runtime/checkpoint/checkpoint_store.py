from typing import Protocol

from runtime.checkpoint.checkpoint import Checkpoint


class CheckpointStore(Protocol):

    async def save(self, checkpoint_id: str, checkpoint: Checkpoint) -> None:
        pass

    async def load(self, checkpoint_id: str) -> Checkpoint | None:
       pass

    async def delete(self, checkpoint_id: str) -> None:
        pass