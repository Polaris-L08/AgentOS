from context.variable_manager import (
    VariableManager
)
from context.variable_state import (
    VariableState
)


def test_set_variable():

    manager = VariableManager()

    state = VariableState()

    state2 = manager.set(
        state,
        "repo_type",
        "python"
    )

    assert (
        state2.variables["repo_type"]
        == "python"
    )

    assert state.variables == {}


def test_remove_variable():

    manager = VariableManager()

    state = VariableState()

    state = manager.set(
        state,
        "repo_type",
        "python"
    )

    state = manager.remove(
        state,
        "repo_type"
    )

    assert state.variables == {}