from __future__ import annotations

from sqlalchemy import delete, select

from runtime.checkpoint import Checkpoint, CheckpointStore
from runtime.persistence.models import CheckpointRecord
from runtime.persistence.postgres import PostgresDatabase


class PostgresCheckpointStore(CheckpointStore):
    """
    PostgreSQL implementation of CheckpointStore.
    """

    def __init__(
        self,
        database: PostgresDatabase,
    ) -> None:
        self._database = database

    async def save(
        self,
        checkpoint_id: str,
        checkpoint: Checkpoint,
    ) -> None:
        record = CheckpointRecord(
            checkpoint_id=checkpoint_id,
            runtime_id=checkpoint.runtime_id,
            task_id=checkpoint.task_id,
            state=checkpoint.model_dump(mode="json"),
        )

        async with self._database.session() as session:
            await session.merge(record)
            await session.commit()

    async def load(
        self,
        checkpoint_id: str,
    ) -> Checkpoint | None:
        async with self._database.session() as session:
            result = await session.execute(
                select(CheckpointRecord).where(
                    CheckpointRecord.checkpoint_id == checkpoint_id
                )
            )

            record = result.scalar_one_or_none()

            if record is None:
                return None

            return Checkpoint.model_validate(record.state)

    async def delete(
        self,
        checkpoint_id: str,
    ) -> None:
        async with self._database.session() as session:
            await session.execute(
                delete(CheckpointRecord).where(
                    CheckpointRecord.checkpoint_id == checkpoint_id
                )
            )

            await session.commit()