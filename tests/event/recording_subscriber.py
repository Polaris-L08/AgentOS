from typing import List

from runtime.events.event import Event


class RecordingSubscriber:

    def __init__(self):
        self.events: List[Event] = []

    def handle(self, event: Event) -> None:
        self.events.append(event)