from context.memory_item import (
    MemoryItem
)
from context.memory_manager import (
    MemoryManager
)
from context.memory_state import (
    MemoryState
)


def test_store_memory():

    manager = MemoryManager()

    state = MemoryState()

    item = MemoryItem(
        content="repo uses uv"
    )

    new_state = manager.store(
        state,
        item
    )

    assert len(new_state.items) == 1

    assert (
        new_state.items[0].content
        == "repo uses uv"
    )

    assert len(state.items) == 0


def test_forget_memory():

    manager = MemoryManager()

    item1 = MemoryItem(
        content="repo uses uv"
    )

    item2 = MemoryItem(
        content="framework pytest"
    )

    state = MemoryState()

    state = manager.store(
        state,
        item1
    )

    state = manager.store(
        state,
        item2
    )

    new_state = manager.forget(
        state,
        item1.id
    )

    assert len(new_state.items) == 1

    assert (
        new_state.items[0].content
        == "framework pytest"
    )


def test_clear_memory():

    manager = MemoryManager()

    state = MemoryState()

    item = MemoryItem(
        content="repo uses uv"
    )

    state = manager.store(
        state,
        item
    )

    state = manager.clear(
        state
    )

    assert len(state.items) == 0