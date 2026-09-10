from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionState(BaseModel):
    """
    Durable representation of a Session.

    SessionState contains only logical session information that can be
    persisted and reconstructed after a process restart.

    It does not contain live runtime objects such as RuntimeContext,
    ExecutionRuntime, ExecutionHandle, asyncio.Task, or tracing objects.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)