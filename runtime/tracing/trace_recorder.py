from abc import ABC, abstractmethod


class TraceRecorder(ABC):

    @abstractmethod
    def start_span(self):
        pass

    @abstractmethod
    def end_span(self):
        pass