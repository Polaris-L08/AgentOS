from pydantic import BaseModel

from runtime.context.message import Message


class HistoryState(BaseModel):

    messages: list[Message] = []