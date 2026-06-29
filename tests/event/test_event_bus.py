from runtime.events.event import Event
from runtime.events import EventBus
from runtime.events.subscriber import EventSubscriber


class DummySubscriber(EventSubscriber):

    def __init__(self):
        self.events = []

    def handle(self, event):
        self.events.append(event)


event = Event(
    type="tool.executed",
    source="tool.py",
    trace_id="123",
    payload={"name": "test"},
)

bus = EventBus()

dummy = DummySubscriber()

bus.subscribe("tool.executed", dummy)

bus.emit(event)


len(dummy.events) == 1