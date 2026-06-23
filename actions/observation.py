from dataclasses import field

from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    success: bool

    content: str

    metadata: dict[str, str] = field(default_factory=dict)