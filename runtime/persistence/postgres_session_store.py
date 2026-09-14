from __future__ import annotations

from sqlalchemy import delete, select

from runtime.persistence.models import SessionRecord
from runtime.persistence.postgres import PostgresDatabase
from runtime.persistence.session_store import SessionStore
from runtime.session.session_state import SessionState


class PostgresSessionStore(SessionStore):
    """
    PostgreSQL implementation of SessionStore.
    """

    def __init__(
        self,
        database: PostgresDatabase,
    ) -> None:
        self._database = database

    async def save(
        self,
        state: SessionState,
    ) -> None:
        async with self._database.session() as session:
            record = SessionRecord(
                session_id=state.session_id,
                created_at=state.created_at,
                metadata_=dict(state.metadata),
            )

            await session.merge(record)
            await session.commit()

    async def load(
        self,
        session_id: str,
    ) -> SessionState | None:
        async with self._database.session() as session:
            result = await session.execute(
                select(SessionRecord).where(
                    SessionRecord.session_id == session_id
                )
            )

            record = result.scalar_one_or_none()

            if record is None:
                return None

            return SessionState(
                session_id=record.session_id,
                created_at=record.created_at,
                metadata=dict(record.metadata_),
            )

    async def delete(
        self,
        session_id: str,
    ) -> None:
        async with self._database.session() as session:
            await session.execute(
                delete(SessionRecord).where(
                    SessionRecord.session_id == session_id
                )
            )

            await session.commit()