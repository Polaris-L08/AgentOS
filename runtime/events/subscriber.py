from abc import ABC, abstractmethod

from runtime.events.event import Event


class EventSubscriber(ABC):

    @abstractmethod
    def handle(self, event: Event) -> None:
        """
        Handle an emittef events.
        """
        pass
