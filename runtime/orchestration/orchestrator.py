from __future__ import annotations

from abc import ABC, abstractmethod

from agents import AgentResult
from agents.base_agent import BaseAgent
from models.task_request import TaskRequest
from runtime.agents.agent_registry import AgentRegistry
from runtime.checkpoint import Checkpoint
from runtime.execution import AgentRuntime, ExecutionHandle


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
        - Application lifecycle
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        agent_runtime: AgentRuntime,
    ) -> None:
        self._agent_registry = agent_registry
        self._agent_runtime = agent_runtime

    @property
    def agent_registry(self) -> AgentRegistry:
        return self._agent_registry

    @property
    def agent_runtime(self) -> AgentRuntime:
        return self._agent_runtime

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