from runtime.persistence.in_memory_execution_store import (
    InMemoryExecutionStore,
)
from runtime.persistence.in_memory_session_store import (
    InMemorySessionStore,
)
from runtime.persistence.persistence_config import PersistenceConfig
from runtime.persistence.persistence_mode import PersistenceMode
from runtime.persistence.persistence_store_factory import (
    PersistenceStoreFactory,
)


def test_factory_creates_in_memory_session_store() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    store = PersistenceStoreFactory.create_session_store(config)

    assert isinstance(store, InMemorySessionStore)


def test_factory_creates_in_memory_execution_store() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    store = PersistenceStoreFactory.create_execution_store(config)

    assert isinstance(store, InMemoryExecutionStore)


def test_factory_creates_both_in_memory_stores() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    session_store, execution_store = (
        PersistenceStoreFactory.create_stores(config)
    )

    assert isinstance(session_store, InMemorySessionStore)
    assert isinstance(execution_store, InMemoryExecutionStore)