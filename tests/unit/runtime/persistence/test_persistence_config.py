import pytest

from runtime.persistence.database_config import DatabaseConfig
from runtime.persistence.persistence_config import PersistenceConfig
from runtime.persistence.persistence_mode import PersistenceMode


def test_default_persistence_mode_is_in_memory() -> None:
    config = PersistenceConfig()

    assert config.mode is PersistenceMode.IN_MEMORY
    assert config.database is None


def test_in_memory_configuration_is_valid() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.IN_MEMORY,
    )

    config.validate_configuration()


def test_postgres_configuration_requires_database() -> None:
    config = PersistenceConfig(
        mode=PersistenceMode.POSTGRES,
    )

    with pytest.raises(
        ValueError,
        match="database configuration is required",
    ):
        config.validate_configuration()


def test_postgres_configuration_is_valid() -> None:
    database_config = DatabaseConfig(
        database_url=(
            "postgresql+asyncpg://agentos:agentos@192.168.0.170:5432/agentos"
        ),
    )

    config = PersistenceConfig(
        mode=PersistenceMode.POSTGRES,
        database=database_config,
    )

    config.validate_configuration()


def test_unknown_configuration_fields_are_rejected() -> None:
    with pytest.raises(ValueError):
        PersistenceConfig(
            unsupported_field=True,
        )