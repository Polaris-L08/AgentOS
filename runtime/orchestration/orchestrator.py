from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from agents import AgentResult
from agents.base_agent import BaseAgent
from models.task_request import TaskRequest
from runtime.checkpoint import Checkpoint
from runtime.execution import ExecutionHandle

if TYPE_CHECKING:
    from runtime.application.application import AgentApplication


class OrchestrationResult:
    """
    Result returned by an Orchestrator.

    The AgentResult represents the actual Agent execution result,
    while the Agent reference identifies the orchestration entry
    Agent that produced the Application-level result.
    """

    def __init__(
        self,
        *,
        agent: BaseAgent,
        agent_result: AgentResult,
    ) -> None:
        self.agent = agent
        self.agent_result = agent_result


class Orchestrator(ABC):
    """
    Application-level orchestration boundary.

    The Orchestrator decides which Agent represents the entry point
    of an Application execution and how an execution is continued.

    Responsibilities:
        - resolve the orchestration entry Agent
        - start normal orchestration
        - resume orchestration from a Checkpoint

    It does NOT own:
        - Execution lifecycle
        - RuntimeContext lifecycle
        - persistence
        - AgentRuntime implementation
        - Checkpoint storage
    """

    def __init__(
        self,
        application: "AgentApplication",
    ) -> None:
        self._application = application

    @abstractmethod
    def resolve_entry_agent(self) -> BaseAgent:
        """
        Resolve the Agent that represents the entry point of the
        current orchestration strategy.
        """
        raise NotImplementedError

    @abstractmethod
    async def execute(
        self,
        task: TaskRequest,
        execution_handle: ExecutionHandle,
    ) -> OrchestrationResult:
        """
        Start a new orchestration execution.
        """
        raise NotImplementedError

    @abstractmethod
    async def resume(
        self,
        task: TaskRequest,
        execution_handle: ExecutionHandle,
        checkpoint: Checkpoint,
        entry_agent_id: str,
    ) -> OrchestrationResult:
        """
        Resume orchestration from a durable Checkpoint.

        The entry Agent MUST be identified from durable Execution
        state rather than selected as a new default Agent.
        """
        raise NotImplementedError