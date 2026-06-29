from abc import ABC, abstractmethod

from runtime.events.event import Event


class EventPublisher(ABC):

    @abstractmethod
    def emit(self, event: Event) -> None:
        """
        Publish an events.
        """
        pass
