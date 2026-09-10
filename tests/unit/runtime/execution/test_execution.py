from datetime import datetime, timezone

import pytest

from runtime.execution import (
    Execution,
    ExecutionLifecycleError,
    ExecutionState,
    ExecutionStatus,
)


def test_execution_starts_in_created_state():
    execution = Execution(
        execution_id="execution-001",
    )

    assert execution.execution_id == "execution-001"
    assert execution.status == ExecutionStatus.CREATED


def test_execution_can_start():
    execution = Execution(
        execution_id="execution-001",
    )

    execution.start()

    assert execution.status == ExecutionStatus.RUNNING


def test_execution_can_pause_and_resume():
    execution = Execution(
        execution_id="execution-001",
    )

    execution.start()
    execution.pause()

    assert execution.status == ExecutionStatus.PAUSED

    execution.resume()

    assert execution.status == ExecutionStatus.RUNNING


@pytest.mark.parametrize(
    "operation, expected_status",
    [
        ("complete", ExecutionStatus.COMPLETED),
        ("fail", ExecutionStatus.FAILED),
        ("cancel", ExecutionStatus.CANCELLED),
    ],
)
def test_running_execution_can_reach_terminal_state(
    operation,
    expected_status,
):
    execution = Execution(
        execution_id="execution-001",
    )

    execution.start()

    getattr(execution, operation)()

    assert execution.status == expected_status


def test_created_execution_cannot_pause():
    execution = Execution(
        execution_id="execution-001",
    )

    with pytest.raises(ExecutionLifecycleError):
        execution.pause()


def test_created_execution_cannot_complete():
    execution = Execution(
        execution_id="execution-001",
    )

    with pytest.raises(ExecutionLifecycleError):
        execution.complete()


def test_created_execution_cannot_fail():
    execution = Execution(
        execution_id="execution-001",
    )

    with pytest.raises(ExecutionLifecycleError):
        execution.fail()


def test_created_execution_cannot_cancel():
    execution = Execution(
        execution_id="execution-001",
    )

    with pytest.raises(ExecutionLifecycleError):
        execution.cancel()


def test_running_execution_cannot_resume():
    execution = Execution(
        execution_id="execution-001",
    )

    execution.start()

    with pytest.raises(ExecutionLifecycleError):
        execution.resume()


@pytest.mark.parametrize(
    "operation",
    [
        "start",
        "pause",
        "resume",
        "complete",
        "fail",
        "cancel",
    ],
)
def test_terminal_execution_cannot_transition_again(operation):
    execution = Execution(
        execution_id="execution-001",
    )

    execution.start()
    execution.complete()

    with pytest.raises(ExecutionLifecycleError):
        getattr(execution, operation)()


def test_execution_snapshot_contains_logical_state():
    execution = Execution(
        execution_id="execution-001",
        task_id="task-001",
        session_id="session-001",
        metadata={
            "source": "test",
        },
    )

    execution.start()
    execution.pause()

    state = execution.snapshot()

    assert isinstance(state, ExecutionState)
    assert state.execution_id == "execution-001"
    assert state.status == ExecutionStatus.PAUSED
    assert state.task_id == "task-001"
    assert state.session_id == "session-001"
    assert state.metadata == {
        "source": "test",
    }


def test_snapshot_is_detached_from_execution():
    execution = Execution(
        execution_id="execution-001",
        metadata={
            "source": "test",
        },
    )

    state = execution.snapshot()

    state.metadata["source"] = "modified"

    assert execution.metadata == {
        "source": "test",
    }


def test_execution_can_be_reconstructed_from_state():
    created_at = datetime(
        2026,
        9,
        10,
        10,
        0,
        tzinfo=timezone.utc,
    )

    original = Execution(
        execution_id="execution-001",
        task_id="task-001",
        session_id="session-001",
        metadata={
            "source": "test",
        },
        created_at=created_at,
    )

    original.start()
    original.pause()

    state = original.snapshot()

    restored = Execution.from_state(state)

    assert restored.execution_id == original.execution_id
    assert restored.status == original.status
    assert restored.task_id == original.task_id
    assert restored.session_id == original.session_id
    assert restored.metadata == original.metadata

    restored.resume()

    assert restored.status == ExecutionStatus.RUNNING
    assert original.status == ExecutionStatus.PAUSED


def test_execution_state_is_serializable():
    execution = Execution(
        execution_id="execution-001",
        task_id="task-001",
        session_id="session-001",
    )

    execution.start()

    state = execution.snapshot()
    data = state.model_dump(mode="json")

    assert data["execution_id"] == "execution-001"
    assert data["status"] == "RUNNING"
    assert data["task_id"] == "task-001"
    assert data["session_id"] == "session-001"