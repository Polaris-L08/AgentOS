from __future__ import annotations

from agents.base_agent import BaseAgent
from runtime.execution import AgentRuntime
from runtime.execution.execution_runtime import ExecutionRuntime


class AgentApplication:
    """
    Application-level boundary for an AgentOS application.

    Application owns long-lived Agent instances and the runtime
    services used by those agents.

    Lifecycle:

        Application
            |
            +---- Agent instances
            |
            +---- AgentRuntime
            |
            +---- ExecutionRuntime

    Application does NOT execute an Agent directly.

    Agent invocation remains the responsibility of AgentRuntime.

    Execution-specific state remains the responsibility of
    ExecutionRuntime / RuntimeContext.

    Session and Application lifecycle management will be added
    in later Phase12 lessons.
    """
    def __init__(
            self,
            application_id: str,
            name: str,
            agent_runtime: AgentRuntime,
            execution_runtime: ExecutionRuntime,
            agents: list[BaseAgent] | None = None,
    ) -> None:
        self.application_id = application_id
        self.name = name
        self.agent_runtime = agent_runtime
        self.execution_runtime = execution_runtime

        self._agents: dict[str, BaseAgent] = {}

        for agent in agents or []:
            self.add_agent(agent)

    def add_agent(self, agent: BaseAgent) -> None:
        """
        Add an Agent instance to this Application.

        The Application becomes the owner of the Agent instance.

        Agent instances are keyed by their stable AgentIdentity.agent_id.
        """

        agent_id = agent.identity.agent_id

        if agent_id in self._agents:
            raise ValueError(
                f"Agent already exists in Application: {agent_id}"
            )

        self._agents[agent_id] = agent

    def get_agent(self, agent_id: str) -> BaseAgent:
        """
        Return an Agent instance owned by this Application.

        Raises:
            KeyError:
                If the Agent does not exist.
        """

        try:
            return self._agents[agent_id]
        except KeyError:
            raise KeyError(
                f"Agent not found in Application: {agent_id}"
            ) from None

    @property
    def agents(self) -> tuple[BaseAgent, ...]:
        """
        Return all Agent instances owned by this Application.

        A tuple is returned so callers cannot mutate the internal
        Application ownership collection directly.
        """

        return tuple(self._agents.values())

    def has_agent(self, agent_id: str) -> bool:
        """
        Check whether an Agent is owned by this Application.
        """

        return agent_id in self._agents