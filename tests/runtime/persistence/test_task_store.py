import asyncio

from models.task_request import TaskRequest
from runtime.persistence.in_memory_task_store import InMemoryTaskStore


def run_async(coro):
    return asyncio.run(coro)


def test_save_and_load_task():
    async def scenario():
        store = InMemoryTaskStore()

        task = TaskRequest(
            task_id="task-1",
            user_input="analyze NVIDIA",
            session_id="session-1",
        )

        await store.save(task)

        loaded = await store.load("task-1")

        assert loaded == task
        assert loaded is not task

    run_async(scenario())


def test_load_returns_none_when_task_does_not_exist():
    async def scenario():
        store = InMemoryTaskStore()

        loaded = await store.load("task-missing")

        assert loaded is None

    run_async(scenario())


def test_save_replaces_existing_task_with_same_id():
    async def scenario():
        store = InMemoryTaskStore()

        first = TaskRequest(
            task_id="task-1",
            user_input="first request",
            session_id="session-1",
        )

        second = TaskRequest(
            task_id="task-1",
            user_input="second request",
            session_id="session-2",
        )

        await store.save(first)
        await store.save(second)

        loaded = await store.load("task-1")

        assert loaded == second
        assert loaded.user_input == "second request"
        assert loaded.session_id == "session-2"

    run_async(scenario())


def test_delete_task():
    async def scenario():
        store = InMemoryTaskStore()

        task = TaskRequest(
            task_id="task-1",
            user_input="analyze NVIDIA",
        )

        await store.save(task)

        assert await store.load("task-1") == task

        await store.delete("task-1")

        assert await store.load("task-1") is None

    run_async(scenario())


def test_delete_nonexistent_task_is_safe():
    async def scenario():
        store = InMemoryTaskStore()

        await store.delete("task-missing")

        assert await store.load("task-missing") is None

    run_async(scenario())


def test_loaded_task_is_independent_from_store():
    async def scenario():
        store = InMemoryTaskStore()

        task = TaskRequest(
            task_id="task-1",
            user_input="original request",
            session_id="session-1",
        )

        await store.save(task)

        loaded = await store.load("task-1")
        loaded_again = await store.load("task-1")

        assert loaded == loaded_again
        assert loaded is not loaded_again

    run_async(scenario())