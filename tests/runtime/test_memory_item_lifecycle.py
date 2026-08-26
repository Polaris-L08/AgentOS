from datetime import datetime, timedelta, timezone

from runtime.context.memory_item import MemoryItem
from runtime.context.memory_metadata import MemoryMetadata


def test_memory_without_expiration_never_expires():

    item = MemoryItem(
        content="long term memory"
    )

    assert item.is_expired() is False


def test_future_memory_does_not_expire():

    now = datetime.now(timezone.utc)

    metadata = MemoryMetadata(
        created_at=now,
        expires_at=now + timedelta(
            hours=1
        ),
    )

    item = MemoryItem(
        content="temporary memory",
        metadata=metadata,
    )

    assert item.is_expired() is False


def test_past_memory_is_expired():

    now = datetime.now(timezone.utc)

    metadata = MemoryMetadata(
        created_at=now - timedelta(
            hours=2
        ),
        expires_at=now - timedelta(
            hours=1
        ),
    )

    item = MemoryItem(
        content="expired memory",
        metadata=metadata,
    )

    assert item.is_expired() is True


def test_expiration_at_current_time_is_expired():

    now = datetime.now(timezone.utc)

    metadata = MemoryMetadata(
        created_at=now - timedelta(
            hours=1
        ),
        expires_at=now,
    )

    item = MemoryItem(
        content="expired memory",
        metadata=metadata,
    )

    assert item.is_expired() is True