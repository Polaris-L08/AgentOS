from abc import ABC, abstractmethod

from event.event import Event


class EventPublisher(ABC):

    @abstractmethod
    def emit(self, event: Event) -> None:
        """
        Publish an event.
        """
        pass
