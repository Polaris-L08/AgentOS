from __future__ import annotations

from sqlalchemy import delete, select

from models.task_request import TaskRequest
from runtime.persistence.models import TaskRecord
from runtime.persistence.postgres import PostgresDatabase
from runtime.persistence.task_store import TaskStore


class PostgresTaskStore(TaskStore):
    """
    PostgreSQL implementation of TaskStore.
    """

    def __init__(
        self,
        database: PostgresDatabase,
    ) -> None:
        self._database = database

    async def save(
        self,
        task: TaskRequest,
    ) -> None:
        async with self._database.session() as session:
            record = TaskRecord(
                task_id=task.task_id,
                user_input=task.user_input,
                session_id=task.session_id,
            )

            await session.merge(record)
            await session.commit()

    async def load(
        self,
        task_id: str,
    ) -> TaskRequest | None:
        async with self._database.session() as session:
            result = await session.execute(
                select(TaskRecord).where(
                    TaskRecord.task_id == task_id
                )
            )

            record = result.scalar_one_or_none()

            if record is None:
                return None

            return TaskRequest(
                task_id=record.task_id,
                user_input=record.user_input,
                session_id=record.session_id,
            )

    async def delete(
        self,
        task_id: str,
    ) -> None:
        async with self._database.session() as session:
            await session.execute(
                delete(TaskRecord).where(
                    TaskRecord.task_id == task_id
                )
            )

            await session.commit()