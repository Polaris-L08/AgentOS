from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ExecutionStatus(StrEnum):
    """
    Lifecycle status of a logical Execution.
    """

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExecutionState(BaseModel):
    """
    Durable representation of a logical Execution.

    ExecutionState describes the logical lifecycle and metadata of
    an Execution. It does not represent the live Runtime that is
    currently executing the Execution.

    In particular, ExecutionState does not contain:

    - RuntimeContext
    - ExecutionHandle
    - AgentExecutionContext
    - asyncio.Task
    - network connections
    - LLM clients
    """

    execution_id: str

    status: ExecutionStatus = ExecutionStatus.CREATED

    task_id: str | None = None

    session_id: str | None = None

    current_checkpoint_id: str | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )