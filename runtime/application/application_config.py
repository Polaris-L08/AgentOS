from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    """
    Declarative configuration for an AgentApplication.

    ApplicationConfig describes what the application should look like.
    It does not create or own runtime components.
    """

    application_id: str
    name: str