from context.scratchpad_state import ScratchpadState


class ScratchpadManager:

    def update_goal(self, state: ScratchpadState, goal: str) -> ScratchpadState:
        return state.model_copy(
            update={
                "scratchpad":
                    state.scratchpad.model_copy(
                        update={
                            "current_goal": goal
                        }
                    )
            }
        )

    def update_hypothesis(self, state: ScratchpadState, hypothesis: str) -> ScratchpadState:
        return state.model_copy(
            update={
                "scratchpad":
                    state.scratchpad.model_copy(
                        update={
                            "hypothesis": hypothesis
                        }
                    )
            }
        )

    def update_next_action(self, state: ScratchpadState, action: str) -> ScratchpadState:

        return state.model_copy(
            update={
                "scratchpad":
                    state.scratchpad.model_copy(
                        update={
                            "next_action": action
                        }
                    )
            }
        )

    def add_note(self, state: ScratchpadState, note: str) -> ScratchpadState:
        notes = [
            *state.scratchpad.notes,
            note
        ]

        return state.model_copy(
            update={
                "scratchpad":
                    state.scratchpad.model_copy(
                        update={
                            "notes": notes
                        }
                    )
            }
        )

    def reset(self, state: ScratchpadState) -> ScratchpadState:
        return ScratchpadState()