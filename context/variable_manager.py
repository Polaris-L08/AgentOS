from typing import Any

from context.variable_state import VariableState


class VariableManager:

    def set(self, state: VariableState, key: str, value: str) -> VariableState:
        new_variables = {
            **state.variables,
            key: value
        }

        return state.model_copy(
            update={
                "variables": new_variables
            }
        )

    def get(self, state: VariableState, key: str, default: Any = None) -> Any:
        return state.variables.get(key, default)

    def remove(self, state: VariableState, key: str) -> VariableState:
        new_variables = dict(state.variables)

        new_variables.pop(key, None)

        return state.model_copy(
            update={
                "variables": new_variables
            }
        )

    def clear(self, state: VariableState) -> VariableState:
        return VariableState()