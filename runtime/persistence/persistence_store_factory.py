from __future__ import annotations

from runtime.persistence.execution_store import ExecutionStore
from runtime.persistence.in_memory_execution_store import (
    InMemoryExecutionStore,
)
from runtime.persistence.in_memory_session_store import (
    InMemorySessionStore,
)
from runtime.persistence.persistence_config import PersistenceConfig
from runtime.persistence.persistence_mode import PersistenceMode
from runtime.persistence.persistence_store_bundle import PersistenceStoreBundle
from runtime.persistence.postgres import PostgresDatabase
from runtime.persistence.postgres_execution_store import (
    PostgresExecutionStore,
)
from runtime.persistence.postgres_session_store import (
    PostgresSessionStore,
)
from runtime.persistence.session_store import SessionStore


class PersistenceStoreFactory:
    """
    Creates persistence implementations according to PersistenceConfig.

    Application depends on the abstract SessionStore and ExecutionStore
    contracts, while this factory owns implementation selection.
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
    def create_stores(
        config: PersistenceConfig,
    ) -> tuple[SessionStore, ExecutionStore]:
        """
        Create both SessionStore and ExecutionStore.

        Returns:
            A tuple containing:

            - SessionStore
            - ExecutionStore
        """

        return (
            PersistenceStoreFactory.create_session_store(config),
            PersistenceStoreFactory.create_execution_store(config),
        )

    @staticmethod
    def create_store_bundle(
            config: PersistenceConfig,
            *,
            create_session_store: bool = True,
            create_execution_store: bool = True,
    ) -> PersistenceStoreBundle:
        """
        Create persistence stores together with their owned resources.

        Only requested stores are created.

        This method is used by ApplicationAssembly when one or more
        persistence stores must be supplied by PersistenceConfig.
        """

        if not create_session_store and not create_execution_store:
            raise ValueError(
                "At least one persistence store must be created."
            )

        config.validate_configuration()

        resources: list[PostgresDatabase] = []

        session_store = None
        execution_store = None

        if config.mode is PersistenceMode.IN_MEMORY:
            if create_session_store:
                session_store = InMemorySessionStore()
            if create_execution_store:
                execution_store = InMemoryExecutionStore()

        elif config.mode is PersistenceMode.POSTGRES:
            database = PostgresDatabase(config.database)

            resources.append(database)

            if create_session_store:
                session_store = PostgresSessionStore(database)
            if create_execution_store:
                execution_store = PostgresExecutionStore(database)
        else:
            raise ValueError(
                f"Unsupported persistence mode: {config.mode}"
            )

        if session_store is None:
            # The caller requested only the execution store.
            #
            # AgentApplication will supply the explicit session store.
            #
            # The field is intentionally typed at runtime as None here
            # and validated by ApplicationAssembly.
            pass

        if execution_store is None:
            # The caller requested only the session store.
            #
            # AgentApplication will supply the explicit execution store.
            pass

        return PersistenceStoreBundle(
            session_store=session_store,
            execution_store=execution_store,
            resources=tuple(resources),
        )