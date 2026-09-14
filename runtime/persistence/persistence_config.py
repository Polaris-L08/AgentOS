from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from runtime.persistence.database_config import DatabaseConfig
from runtime.persistence.persistence_mode import PersistenceMode


class PersistenceConfig(BaseModel):
    """
    Configuration used to select persistence implementations.

    The default mode is IN_MEMORY so that AgentOS can run without
    an external database.
    """

    model_config = ConfigDict(extra="forbid")

    mode: PersistenceMode = PersistenceMode.IN_MEMORY
    database: DatabaseConfig | None = Field(default=None)

    def validate_configuration(self) -> None:
        """
        Validate configuration according to the selected persistence mode.

        PostgreSQL mode requires database configuration.
        In-memory mode does not require database configuration.
        """

        if self.mode is PersistenceMode.POSTGRES and self.database is None:
            raise ValueError(
                "database configuration is required when persistence "
                "mode is POSTGRES"
            )