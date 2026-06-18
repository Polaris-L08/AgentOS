from context.scratchpad_manager import ScratchpadManager
from context.scratchpad_state import ScratchpadState


def test_update_goal():

    manager = ScratchpadManager()

    state = ScratchpadState()

    new_state = manager.update_goal(
        state,
        "fix pytest"
    )

    assert (
        new_state.scratchpad.current_goal
        == "fix pytest"
    )

    # old state unchanged
    assert (
        state.scratchpad.current_goal
        == ""
    )


def test_add_note():

    manager = ScratchpadManager()

    state = ScratchpadState()

    state2 = manager.add_note(
        state,
        "ImportError found"
    )

    state3 = manager.add_note(
        state2,
        "Need inspect pyproject"
    )

    assert state3.scratchpad.notes == [
        "ImportError found",
        "Need inspect pyproject"
    ]

    assert state.scratchpad.notes == []


def test_reset():

    manager = ScratchpadManager()

    state = ScratchpadState()

    state = manager.update_goal(
        state,
        "fix pytest"
    )

    state = manager.add_note(
        state,
        "ImportError found"
    )

    new_state = manager.reset(
        state
    )

    assert (
        new_state.scratchpad.current_goal
        == ""
    )

    assert (
        new_state.scratchpad.notes
        == []
    )

