from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DatabaseConfig(BaseModel):
    """
    Configuration for the PostgreSQL persistence adapter.

    This model contains infrastructure configuration only.
    It does not belong to the Runtime Core.
    """

    model_config = ConfigDict(extra="forbid")

    database_url: str = Field(
        min_length=1,
    )

    echo: bool = False

    pool_pre_ping: bool = True