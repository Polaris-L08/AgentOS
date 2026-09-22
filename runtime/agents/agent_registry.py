from __future__ import annotations

from agents.base_agent import BaseAgent


class AgentRegistry:
    """
    Registry for Agents owned by an Application Runtime.

    AgentRegistry is responsible only for Agent registration and lookup.

    It does NOT:
        - execute Agents
        - orchestrate Agents
        - manage Agent lifecycle
        - persist Agents
        - manage Application lifecycle
    """

    def __init__(
        self,
        agents: list[BaseAgent] | None = None,
    ) -> None:
        self._agents: dict[str, BaseAgent] = {}

        for agent in agents or []:
            self.register(agent)

    @property
    def agents(self) -> tuple[BaseAgent, ...]:
        return tuple(self._agents.values())

    def register(self, agent: BaseAgent) -> None:
        agent_id = agent.identity.agent_id

        if agent_id in self._agents:
            raise ValueError(
                f"Agent already registered: {agent_id}"
            )

        self._agents[agent_id] = agent

    def get(self, agent_id: str) -> BaseAgent:
        try:
            return self._agents[agent_id]
        except KeyError:
            raise KeyError(
                f"Agent not found: {agent_id}"
            ) from None

    def has(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def all(self) -> tuple[BaseAgent, ...]:
        return self.agents