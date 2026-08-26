from datetime import datetime, timedelta, timezone

from runtime.context.memory_metadata import MemoryMetadata


def test_memory_metadata_has_created_at_by_default():

    metadata = MemoryMetadata()

    assert metadata.created_at.tzinfo is not None


def test_memory_metadata_can_have_expiration():

    now = datetime.now(timezone.utc)

    expires_at = now + timedelta(
        hours=1
    )

    metadata = MemoryMetadata(
        created_at=now,
        expires_at=expires_at,
    )

    assert metadata.created_at == now
    assert metadata.expires_at == expires_at