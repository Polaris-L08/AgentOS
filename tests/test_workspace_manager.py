from context.workspace_manager import (
    WorkspaceManager
)
from context.workspace_state import (
    WorkspaceState
)


def test_set_current_file():

    manager = WorkspaceManager()

    state = WorkspaceState()

    new_state = manager.set_current_file(
        state,
        "main.py"
    )

    assert (
        new_state.current_file
        == "main.py"
    )

    assert (
        state.current_file
        == ""
    )