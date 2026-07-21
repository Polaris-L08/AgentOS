from dataclasses import dataclass
from typing import Any


@dataclass
class AgentMessage:

    sender: str

    receiver: str

    message_type: str

    payload: Any

    correlation_id: str | None = None