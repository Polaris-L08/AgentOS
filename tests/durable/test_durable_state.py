from typing import Any

from pydantic import BaseModel

from runtime.durable import DurableState

class ExampleDurableState(BaseModel):
    execution_id: str
    status: str
    metadata: dict[str, Any]

def test_pydantic_state_can_satisfy_durable_state_protocol():
    state = ExampleDurableState(
        execution_id="execution-001",
        status="PAUSED",
        metadata={
        "task_id": "task-001",
        },
    )


    durable_state: DurableState = state

    data = durable_state.model_dump()

    assert data == {
        "execution_id": "execution-001",
        "status": "PAUSED",
        "metadata": {
            "task_id": "task-001",
        },
    }


def test_durable_state_is_data_not_runtime_object():
    state = ExampleDurableState(
    execution_id="execution-001",
    status="CREATED",
    metadata={},
    )


    assert not hasattr(state, "runtime_context")
    assert not hasattr(state, "close")
    assert not hasattr(state, "execute")

