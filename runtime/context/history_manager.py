from history_state import HistoryState
from message import Message

class HistoryManager:

    def append(self, state: HistoryState, message: Message):
        state.messages.append(message)
