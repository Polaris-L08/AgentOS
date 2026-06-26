from typing import List

from event.event import Event


class RecordingSubscriber:

    def __init__(self):
        self.events: List[Event] = []

    def handle(self, event: Event) -> None:
        self.events.append(event)