from pydantic import BaseModel


class HistoryState(BaseModel):

    messages: list[Message] = []