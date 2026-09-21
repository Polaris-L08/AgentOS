from __future__ import annotations

from dataclasses import dataclass

from runtime.checkpoint import CheckpointStore
from runtime.persistence.execution_store import ExecutionStore
from runtime.persistence.postgres import PostgresDatabase
from runtime.persistence.session_store import SessionStore
from runtime.persistence.task_store import TaskStore


@dataclass(frozen=True, slots=True)
class PersistenceStoreBundle:
    """
    Persistence stores together with the resources owned by the
    persistence factory.

    The stores are runtime-facing persistence abstractions.
    The resources represent external resources created by the
    persistence layer, such as SQLAlchemy database engines.
    """

    session_store: SessionStore | None

    execution_store: ExecutionStore | None

    task_store: TaskStore | None

    checkpoint_store: CheckpointStore | None

    resources: tuple[PostgresDatabase, ...] = ()