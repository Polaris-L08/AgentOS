from runtime.context.memory_item import MemoryItem
from runtime.context.memory_state import MemoryState


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

    def retrieve(self, state: MemoryState) -> list[MemoryItem]:
        return state.items

    def clear(self, state: MemoryState) -> MemoryState:
        return MemoryState()

    def forget(self, state: MemoryState, memory_id: str) -> MemoryState:
        items = [
            item
            for item in state.items
            if item.id != memory_id
        ]

        return state.model_copy(
            update={
                "items": items
            }
        )