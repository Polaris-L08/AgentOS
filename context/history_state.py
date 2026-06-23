from pydantic import BaseModel

from context.message import Message


class HistoryState(BaseModel):

    messages: list[Message] = []