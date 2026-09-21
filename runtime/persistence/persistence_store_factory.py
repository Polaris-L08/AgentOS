from __future__ import annotations

from runtime.checkpoint import CheckpointStore
from runtime.persistence.execution_store import ExecutionStore
from runtime.persistence.in_memory_execution_store import (
    InMemoryExecutionStore,
)
from runtime.persistence.in_memory_session_store import (
    InMemorySessionStore,
)
from runtime.persistence.in_memory_task_store import (
    InMemoryTaskStore,
)
from runtime.persistence.persistence_config import PersistenceConfig
from runtime.persistence.persistence_mode import PersistenceMode
from runtime.persistence.persistence_store_bundle import PersistenceStoreBundle
from runtime.persistence.postgres import PostgresDatabase
from runtime.persistence.postgres_checkpoint_store import (
    PostgresCheckpointStore,
)
from runtime.persistence.postgres_execution_store import (
    PostgresExecutionStore,
)
from runtime.persistence.postgres_session_store import (
    PostgresSessionStore,
)
from runtime.persistence.postgres_task_store import (
    PostgresTaskStore,
)
from runtime.persistence.session_store import SessionStore
from runtime.persistence.task_store import TaskStore


class PersistenceStoreFactory:
    """
    Creates persistence implementations according to PersistenceConfig.

    Application depends on persistence contracts, while this factory owns
    implementation selection.
    """

    @staticmethod
    def create_session_store(
        config: PersistenceConfig,
    ) -> SessionStore:
        """
        Create a SessionStore according to the configured mode.
        """

        config.validate_configuration()

        if config.mode is PersistenceMode.IN_MEMORY:
            return InMemorySessionStore()

        if config.mode is PersistenceMode.POSTGRES:
            if config.database is None:
                raise ValueError(
                    "database configuration is required for PostgreSQL"
                )

            database = PostgresDatabase(config.database)

            return PostgresSessionStore(database)

        raise ValueError(
            f"Unsupported persistence mode: {config.mode}"
        )

    @staticmethod
    def create_execution_store(
        config: PersistenceConfig,
    ) -> ExecutionStore:
        """
        Create an ExecutionStore according to the configured mode.
        """

        config.validate_configuration()

        if config.mode is PersistenceMode.IN_MEMORY:
            return InMemoryExecutionStore()

        if config.mode is PersistenceMode.POSTGRES:
            if config.database is None:
                raise ValueError(
                    "database configuration is required for PostgreSQL"
                )

            database = PostgresDatabase(config.database)

            return PostgresExecutionStore(database)

        raise ValueError(
            f"Unsupported persistence mode: {config.mode}"
        )

    @staticmethod
    def create_task_store(
        config: PersistenceConfig,
    ) -> TaskStore:
        """
        Create a TaskStore according to the configured mode.
        """

        config.validate_configuration()

        if config.mode is PersistenceMode.IN_MEMORY:
            return InMemoryTaskStore()

        if config.mode is PersistenceMode.POSTGRES:
            if config.database is None:
                raise ValueError(
                    "database configuration is required for PostgreSQL"
                )

            database = PostgresDatabase(config.database)

            return PostgresTaskStore(database)

        raise ValueError(
            f"Unsupported persistence mode: {config.mode}"
        )

    @staticmethod
    def create_checkpoint_store(
        config: PersistenceConfig,
    ) -> CheckpointStore:
        """
        Create a CheckpointStore according to the configured mode.
        """

        config.validate_configuration()

        if config.mode is PersistenceMode.IN_MEMORY:
            from runtime.checkpoint import MemoryCheckpointStore

            return MemoryCheckpointStore()

        if config.mode is PersistenceMode.POSTGRES:
            if config.database is None:
                raise ValueError(
                    "database configuration is required for PostgreSQL"
                )

            database = PostgresDatabase(config.database)

            return PostgresCheckpointStore(database)

        raise ValueError(
            f"Unsupported persistence mode: {config.mode}"
        )

    @staticmethod
    def create_stores(
        config: PersistenceConfig,
    ) -> tuple[
        SessionStore,
        ExecutionStore,
        TaskStore,
        CheckpointStore,
    ]:
        """
        Create all persistence stores.

        Returns:
            SessionStore
            ExecutionStore
            TaskStore
            CheckpointStore
        """

        return (
            PersistenceStoreFactory.create_session_store(config),
            PersistenceStoreFactory.create_execution_store(config),
            PersistenceStoreFactory.create_task_store(config),
            PersistenceStoreFactory.create_checkpoint_store(config),
        )

    @staticmethod
    def create_store_bundle(
        config: PersistenceConfig,
        *,
        create_session_store: bool = True,
        create_execution_store: bool = True,
        create_task_store: bool = True,
        create_checkpoint_store: bool = True,
    ) -> PersistenceStoreBundle:
        """
        Create persistence stores together with their owned resources.

        Only requested stores are created.
        """

        if not any(
            (
                create_session_store,
                create_execution_store,
                create_task_store,
                create_checkpoint_store,
            )
        ):
            raise ValueError(
                "At least one persistence store must be created."
            )

        config.validate_configuration()

        resources: list[PostgresDatabase] = []

        session_store = None
        execution_store = None
        task_store = None
        checkpoint_store = None

        if config.mode is PersistenceMode.IN_MEMORY:
            if create_session_store:
                session_store = InMemorySessionStore()

            if create_execution_store:
                execution_store = InMemoryExecutionStore()

            if create_task_store:
                task_store = InMemoryTaskStore()

            if create_checkpoint_store:
                from runtime.checkpoint import MemoryCheckpointStore

                checkpoint_store = MemoryCheckpointStore()

        elif config.mode is PersistenceMode.POSTGRES:
            if config.database is None:
                raise ValueError(
                    "database configuration is required for PostgreSQL"
                )

            database = PostgresDatabase(config.database)
            resources.append(database)

            if create_session_store:
                session_store = PostgresSessionStore(database)

            if create_execution_store:
                execution_store = PostgresExecutionStore(database)

            if create_task_store:
                task_store = PostgresTaskStore(database)

            if create_checkpoint_store:
                checkpoint_store = PostgresCheckpointStore(database)

        else:
            raise ValueError(
                f"Unsupported persistence mode: {config.mode}"
            )

        return PersistenceStoreBundle(
            session_store=session_store,
            execution_store=execution_store,
            task_store=task_store,
            checkpoint_store=checkpoint_store,
            resources=tuple(resources),
        )