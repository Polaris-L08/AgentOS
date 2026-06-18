import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    id: str

    role: MessageRole

    content: str

    timestamp: datetime

    metadata: dict[str, Any] = {}
    