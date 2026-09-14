from __future__ import annotations

from enum import StrEnum


class PersistenceMode(StrEnum):
    """
    Supported persistence modes.

    IN_MEMORY:
        Store durable states only in the current process memory.

    POSTGRES:
        Store durable states in PostgreSQL.
    """

    IN_MEMORY = "in_memory"
    POSTGRES = "postgres"