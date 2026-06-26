from abc import ABC, abstractmethod

from event.event import Event


class EventSubscriber(ABC):

    @abstractmethod
    def handle(self, event: Event) -> None:
        """
        Handle an emittef event.
        """
        pass
