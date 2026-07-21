from dataclasses import dataclass


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str

    agent_type: str

    name: str