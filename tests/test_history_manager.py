from context.history_manager import HistoryManager
from context.history_state import HistoryState
from context.message import Message

manager = HistoryManager()

msg = Message()

old_state = HistoryState()

new_state = manager.append(old_state, msg)

print()