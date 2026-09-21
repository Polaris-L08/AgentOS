from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PersistenceBase(DeclarativeBase):
    """
    Base class for PostgreSQL persistence models.

    Persistence models belong to the persistence adapter layer and must not
    be used as runtime state models.
    """


class SessionRecord(PersistenceBase):
    """
    PostgreSQL representation of SessionState.
    """

    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class ExecutionRecord(PersistenceBase):
    """
    PostgreSQL representation of ExecutionState.
    """

    __tablename__ = "executions"

    execution_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    task_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    current_checkpoint_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class TaskRecord(PersistenceBase):
    """
    PostgreSQL representation of TaskRequest.
    """

    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    user_input: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )


class CheckpointRecord(PersistenceBase):
    """
    PostgreSQL representation of a Checkpoint.

    The runtime Checkpoint remains a Pydantic model.
    PostgreSQL stores its serialized representation as JSONB.
    """

    __tablename__ = "checkpoints"

    checkpoint_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    runtime_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    state: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )