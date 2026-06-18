from context.memory_item import MemoryItem
from context.memory_state import MemoryState


class MemoryManager:

    def store(self, state: MemoryState, item: MemoryItem) -> MemoryState:
        return state.model_copy(
            update={
                "items":[
                    *state.items,
                    item
                ]
            }
        )
