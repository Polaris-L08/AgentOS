import uuid
from typing import Any

from pydantic import BaseModel, Field


class ToolRequest(BaseModel):

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    tool_name: str

    arguments: dict[str, Any] = Field(default_factory=dict)