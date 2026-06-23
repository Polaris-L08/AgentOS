from dataclasses import dataclass


@dataclass(frozen=True)
class PromptMessage:
    role: str

    content: str