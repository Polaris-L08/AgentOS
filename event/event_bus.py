from collections import defaultdict

from .event import Event
from .publisher import EventPublisher
from .subscriber import EventSubscriber


class EventBus(EventPublisher):
    """
    Event bus.

    Event bus is a mediator between event publishers and subscribers.
    """
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventSubscriber]] = defaultdict(list)

    def subscribe(self, event_type: str, subscriber: EventSubscriber) -> None:
        # 不做重复判断，Phase8阶段认为重复订阅是调用方的错误。
        self._subscribers[event_type].append(subscriber)

    def unsubscribe(self, event_type: str, subscriber: EventSubscriber) -> None:
        subscribers = self._subscribers.get(event_type)

        if subscribers is None:
            return

        try:
            subscribers.remove(subscriber)
        except ValueError:
            return

        if not subscribers:
            del self._subscribers[event_type]

    def emit(self, event: Event) -> None:

        subscribers = self._subscribers.get(event.type)

        if subscribers is None:
            return

        for subscriber in list(subscribers):
            try:
                subscriber.handle(event)
            except Exception:
                # TODO: integrate Logging Runtime
                pass