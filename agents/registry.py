from typing import Dict

from agents import BaseAgent


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent):
        agent_id = agent.identity.agent_id

        if agent_id in self._agents:
            raise ValueError(f"Agent already exists: {agent_id}")

        self._agents[agent_id] = agent

    def get(self, agent_id: str) -> BaseAgent:
        agent = self._agents.get(agent_id)

        if agent is None:
            raise KeyError(f"Agent not found: {agent_id}")

        return agent

    def remove(self, agent_id: str):
        self._agents.pop(agent_id, None)

    def list_agents(self):
        return list(self._agents.values())