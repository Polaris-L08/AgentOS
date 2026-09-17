from __future__ import annotations

from sqlalchemy import delete, select

from runtime.execution.execution_state import ExecutionState, ExecutionStatus
from runtime.persistence.execution_store import ExecutionStore
from runtime.persistence.models import ExecutionRecord
from runtime.persistence.postgres import PostgresDatabase


class PostgresExecutionStore(ExecutionStore):
    """
    PostgreSQL implementation of ExecutionStore.
    """

    def __init__(
        self,
        database: PostgresDatabase,
    ) -> None:
        self._database = database

    async def save(
        self,
        state: ExecutionState,
    ) -> None:
        async with self._database.session() as session:
            record = ExecutionRecord(
                execution_id=state.execution_id,
                status=state.status.value,
                task_id=state.task_id,
                session_id=state.session_id,
                current_checkpoint_id=state.current_checkpoint_id,
                created_at=state.created_at,
                updated_at=state.updated_at,
            )

            await session.merge(record)
            await session.commit()

    async def load(
        self,
        execution_id: str,
    ) -> ExecutionState | None:
        async with self._database.session() as session:
            result = await session.execute(
                select(ExecutionRecord).where(
                    ExecutionRecord.execution_id == execution_id
                )
            )

            record = result.scalar_one_or_none()

            if record is None:
                return None

            return ExecutionState(
                execution_id=record.execution_id,
                status=ExecutionStatus(record.status),
                task_id=record.task_id,
                session_id=record.session_id,
                current_checkpoint_id=record.current_checkpoint_id,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )

    async def delete(
        self,
        execution_id: str,
    ) -> None:
        async with self._database.session() as session:
            await session.execute(
                delete(ExecutionRecord).where(
                    ExecutionRecord.execution_id == execution_id
                )
            )

            await session.commit()