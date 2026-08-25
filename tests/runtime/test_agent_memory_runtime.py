import pytest

from agents.base_agent import BaseAgent
from agents.identity import AgentIdentity
from agents.agent_result import AgentResult
from models.task_request import TaskRequest
from runtime.context import AgentExecutionContext
from runtime.context.memory_item import MemoryItem
from runtime.execution import AgentRuntime
from runtime.memory import (
    InMemoryMemoryStore,
    MemoryAccessPolicy,
    MemoryOperation,
    MemoryRuntime,
)
from tests.runtime.test_agent_runtime import create_runtime_context


class MockMemoryAgent(BaseAgent):
    async def run(self, task, agent_execution_context):
        return AgentResult(
            success=True,
            output=task.user_input,
        )


# ============================================================
# Lesson3 - Memory Runtime
# ============================================================


@pytest.mark.asyncio
async def test_memory_survives_multiple_executions():
    agent = MockMemoryAgent(
        identity=AgentIdentity(
            agent_id="memory-agent",
            agent_type="test",
            name="MemoryAgent",
        )
    )

    runtime = AgentRuntime()

    context_1 = create_runtime_context()

    execution_1 = AgentExecutionContext.create(
        context_1,
        agent,
    )

    await agent.memory.write(
        MemoryItem(
            content="NVIDIA research completed"
        ),
        context_1,
    )

    await runtime.execute(
        agent=agent,
        task=TaskRequest(
            task_id="task-001",
            user_input="first",
        ),
        runtime_context=context_1,
        agent_execution_context=execution_1,
    )

    context_2 = create_runtime_context()

    execution_2 = AgentExecutionContext.create(
        context_2,
        agent,
    )

    memories = await agent.memory.read(
        context_2
    )

    assert len(memories) == 1

    assert (
        memories[0].content
        == "NVIDIA research completed"
    )

    assert (
        execution_1.agent_context
        is execution_2.agent_context
    )

    assert execution_1 is not execution_2

    assert (
        execution_1.loop
        is not execution_2.loop
    )


@pytest.mark.asyncio
async def test_memory_isolated_between_agents():
    store = InMemoryMemoryStore()

    agent_a = MockMemoryAgent(
        identity=AgentIdentity(
            agent_id="agent-a",
            agent_type="test",
            name="AgentA",
        ),
        memory_store=store,
    )

    agent_b = MockMemoryAgent(
        identity=AgentIdentity(
            agent_id="agent-b",
            agent_type="test",
            name="AgentB",
        ),
        memory_store=store,
    )

    context = create_runtime_context()

    await agent_a.memory.write(
        MemoryItem(
            content="private research memory"
        ),
        context,
    )

    assert len(
        await agent_a.memory.read(context)
    ) == 1

    assert (
        await agent_b.memory.read(context)
        == []
    )


@pytest.mark.asyncio
async def test_memory_query_forget_and_clear():
    agent = MockMemoryAgent(
        identity=AgentIdentity(
            agent_id="memory-agent",
            agent_type="test",
            name="MemoryAgent",
        ),
        memory_access_policy=MemoryAccessPolicy(
            allow_read=True,
            allow_write=True,
            allow_delete=True,
        ),
    )

    context = create_runtime_context()

    first = MemoryItem(
        content="NVIDIA quarterly revenue increased"
    )

    second = MemoryItem(
        content="Apple product research"
    )

    await agent.memory.write(
        first,
        context,
    )

    await agent.memory.write(
        second,
        context,
    )

    matches = await agent.memory.query(
        "nvidia",
        context,
    )

    assert [item.id for item in matches] == [
        first.id
    ]

    await agent.memory.forget(
        first.id,
        context,
    )

    assert await agent.memory.read(
        context
    ) == [second]

    await agent.memory.clear(
        context
    )

    assert await agent.memory.read(
        context
    ) == []


@pytest.mark.asyncio
async def test_memory_runtime_uses_injected_store():
    store = InMemoryMemoryStore()

    agent = MockMemoryAgent(
        identity=AgentIdentity(
            agent_id="memory-agent",
            agent_type="test",
            name="MemoryAgent",
        ),
        memory_store=store,
    )

    context = create_runtime_context()

    item = MemoryItem(
        content="stored externally from AgentContext"
    )

    await agent.memory.write(
        item,
        context,
    )

    # Memory is not stored in AgentContext.
    assert not hasattr(
        agent.context,
        "memory_state",
    )

    # Memory is stored through MemoryStore.
    assert await store.read(
        agent.identity.agent_id
    ) == [item]


# ============================================================
# Lesson4 - MemoryOperation
# ============================================================


def test_memory_operation_values():
    assert MemoryOperation.READ.value == "read"

    assert MemoryOperation.WRITE.value == "write"

    assert MemoryOperation.DELETE.value == "delete"


def test_memory_operation_is_string_enum():
    assert isinstance(
        MemoryOperation.READ,
        str,
    )

    assert isinstance(
        MemoryOperation.WRITE,
        str,
    )

    assert isinstance(
        MemoryOperation.DELETE,
        str,
    )


# ============================================================
# Lesson4 - MemoryAccessPolicy
# ============================================================


def test_memory_access_policy_default_permissions():
    policy = MemoryAccessPolicy()

    assert policy.allows(
        MemoryOperation.READ
    ) is True

    assert policy.allows(
        MemoryOperation.WRITE
    ) is True

    assert policy.allows(
        MemoryOperation.DELETE
    ) is False


def test_memory_access_policy_read_only():
    policy = MemoryAccessPolicy(
        allow_read=True,
        allow_write=False,
        allow_delete=False,
    )

    assert policy.allows(
        MemoryOperation.READ
    ) is True

    assert policy.allows(
        MemoryOperation.WRITE
    ) is False

    assert policy.allows(
        MemoryOperation.DELETE
    ) is False


def test_memory_access_policy_write_only():
    policy = MemoryAccessPolicy(
        allow_read=False,
        allow_write=True,
        allow_delete=False,
    )

    assert policy.allows(
        MemoryOperation.READ
    ) is False

    assert policy.allows(
        MemoryOperation.WRITE
    ) is True

    assert policy.allows(
        MemoryOperation.DELETE
    ) is False


def test_memory_access_policy_delete_enabled():
    policy = MemoryAccessPolicy(
        allow_read=True,
        allow_write=True,
        allow_delete=True,
    )

    assert policy.allows(
        MemoryOperation.READ
    ) is True

    assert policy.allows(
        MemoryOperation.WRITE
    ) is True

    assert policy.allows(
        MemoryOperation.DELETE
    ) is True


def test_memory_access_policy_is_immutable():
    policy = MemoryAccessPolicy()

    with pytest.raises(AttributeError):
        policy.allow_delete = True


# ============================================================
# Lesson4 - MemoryRuntime Access Control
# ============================================================


@pytest.mark.asyncio
async def test_memory_runtime_default_policy_allows_read_and_write_but_denies_delete():
    agent = MockMemoryAgent(
        identity=AgentIdentity(
            agent_id="memory-agent",
            agent_type="test",
            name="MemoryAgent",
        )
    )

    context = create_runtime_context()

    item = MemoryItem(
        content="protected memory"
    )

    # READ and WRITE are allowed.
    await agent.memory.write(
        item,
        context,
    )

    assert await agent.memory.read(
        context
    ) == [item]

    # DELETE is denied by default.
    with pytest.raises(PermissionError):
        await agent.memory.forget(
            item.id,
            context,
        )

    with pytest.raises(PermissionError):
        await agent.memory.clear(
            context,
        )

    # Denied operations must not mutate storage.
    assert await agent.memory.read(
        context
    ) == [item]


@pytest.mark.asyncio
async def test_memory_runtime_read_only_policy():
    store = InMemoryMemoryStore()

    runtime = MemoryRuntime(
        agent_id="read-only-agent",
        store=store,
        access_policy=MemoryAccessPolicy(
            allow_read=True,
            allow_write=False,
            allow_delete=False,
        ),
    )

    context = create_runtime_context()

    # READ is allowed.
    assert await runtime.read(
        context
    ) == []

    # WRITE is denied.
    with pytest.raises(PermissionError):
        await runtime.write(
            MemoryItem(
                content="should not be written"
            ),
            context,
        )

    # DELETE is denied.
    with pytest.raises(PermissionError):
        await runtime.forget(
            "missing",
            context,
        )

    with pytest.raises(PermissionError):
        await runtime.clear(
            context,
        )

    # Store must remain unchanged.
    assert await store.read(
        "read-only-agent"
    ) == []


@pytest.mark.asyncio
async def test_memory_runtime_write_only_policy():
    store = InMemoryMemoryStore()

    runtime = MemoryRuntime(
        agent_id="write-only-agent",
        store=store,
        access_policy=MemoryAccessPolicy(
            allow_read=False,
            allow_write=True,
            allow_delete=False,
        ),
    )

    context = create_runtime_context()

    item = MemoryItem(
        content="write only memory"
    )

    # WRITE is allowed.
    await runtime.write(
        item,
        context,
    )

    # READ is denied.
    with pytest.raises(PermissionError):
        await runtime.read(
            context,
        )

    # QUERY is also a READ operation.
    with pytest.raises(PermissionError):
        await runtime.query(
            "write",
            context,
        )

    # DELETE is denied.
    with pytest.raises(PermissionError):
        await runtime.forget(
            item.id,
            context,
        )

    with pytest.raises(PermissionError):
        await runtime.clear(
            context,
        )

    # The write itself succeeded.
    assert await store.read(
        "write-only-agent"
    ) == [item]


@pytest.mark.asyncio
async def test_memory_runtime_delete_policy():
    store = InMemoryMemoryStore()

    runtime = MemoryRuntime(
        agent_id="deletable-agent",
        store=store,
        access_policy=MemoryAccessPolicy(
            allow_read=True,
            allow_write=True,
            allow_delete=True,
        ),
    )

    context = create_runtime_context()

    item = MemoryItem(
        content="deletable memory"
    )

    await runtime.write(
        item,
        context,
    )

    assert await runtime.read(
        context
    ) == [item]

    # DELETE is explicitly enabled.
    await runtime.forget(
        item.id,
        context,
    )

    assert await runtime.read(
        context
    ) == []


@pytest.mark.asyncio
async def test_memory_runtime_query_uses_read_permission():
    store = InMemoryMemoryStore()

    runtime = MemoryRuntime(
        agent_id="query-agent",
        store=store,
        access_policy=MemoryAccessPolicy(
            allow_read=False,
            allow_write=True,
            allow_delete=False,
        ),
    )

    context = create_runtime_context()

    # query() must use the READ permission.
    with pytest.raises(PermissionError):
        await runtime.query(
            "anything",
            context,
        )