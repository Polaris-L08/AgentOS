from runtime.checkpoint import MemoryCheckpointStore
from runtime.persistence import (
    InMemoryExecutionStore,
    InMemorySessionStore,
    InMemoryTaskStore,
    PersistenceConfig,
    PersistenceMode,
    PersistenceStoreFactory,
)


def test_factory_creates_in_memory_session_store() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    store = PersistenceStoreFactory.create_session_store(
        config,
    )

    assert isinstance(
        store,
        InMemorySessionStore,
    )


def test_factory_creates_in_memory_execution_store() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    store = PersistenceStoreFactory.create_execution_store(
        config,
    )

    assert isinstance(
        store,
        InMemoryExecutionStore,
    )


def test_factory_creates_both_in_memory_stores() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    session_store, execution_store, task_store, checkpoint_store = (
        PersistenceStoreFactory.create_stores(
            config,
        )
    )

    assert isinstance(
        session_store,
        InMemorySessionStore,
    )

    assert isinstance(
        execution_store,
        InMemoryExecutionStore,
    )

    assert isinstance(
        task_store,
        InMemoryTaskStore
    )

    assert isinstance(
        checkpoint_store,
        MemoryCheckpointStore
    )


def test_factory_creates_in_memory_store_bundle() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    bundle = PersistenceStoreFactory.create_store_bundle(
        config,
    )

    assert isinstance(
        bundle.session_store,
        InMemorySessionStore,
    )

    assert isinstance(
        bundle.execution_store,
        InMemoryExecutionStore,
    )

    assert isinstance(
        bundle.task_store,
        InMemoryTaskStore,
    )

    assert isinstance(
        bundle.checkpoint_store,
        MemoryCheckpointStore,
    )

    assert bundle.resources == ()


def test_factory_can_create_only_task_and_checkpoint_stores() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    bundle = PersistenceStoreFactory.create_store_bundle(
        config,
        create_session_store=False,
        create_execution_store=False,
        create_task_store=True,
        create_checkpoint_store=True,
    )

    assert bundle.session_store is None
    assert bundle.execution_store is None

    assert isinstance(
        bundle.task_store,
        InMemoryTaskStore,
    )

    assert isinstance(
        bundle.checkpoint_store,
        MemoryCheckpointStore,
    )

    assert bundle.resources == ()


def test_factory_can_create_only_task_store() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    bundle = PersistenceStoreFactory.create_store_bundle(
        config,
        create_session_store=False,
        create_execution_store=False,
        create_task_store=True,
        create_checkpoint_store=False,
    )

    assert bundle.session_store is None
    assert bundle.execution_store is None

    assert isinstance(
        bundle.task_store,
        InMemoryTaskStore,
    )

    assert bundle.checkpoint_store is None
    assert bundle.resources == ()


def test_factory_can_create_only_checkpoint_store() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    bundle = PersistenceStoreFactory.create_store_bundle(
        config,
        create_session_store=False,
        create_execution_store=False,
        create_task_store=False,
        create_checkpoint_store=True,
    )

    assert bundle.session_store is None
    assert bundle.execution_store is None
    assert bundle.task_store is None

    assert isinstance(
        bundle.checkpoint_store,
        MemoryCheckpointStore,
    )

    assert bundle.resources == ()


def test_factory_requires_at_least_one_store() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    try:
        PersistenceStoreFactory.create_store_bundle(
            config,
            create_session_store=False,
            create_execution_store=False,
            create_task_store=False,
            create_checkpoint_store=False,
        )
    except ValueError as exc:
        assert (
            str(exc)
            == "At least one persistence store must be created."
        )
    else:
        raise AssertionError(
            "Expected ValueError when no persistence store is requested."
        )