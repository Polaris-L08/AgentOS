from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from runtime.session.session import Session
from runtime.session.session_state import SessionState


def test_session_snapshot_creates_durable_state() -> None:
    created_at = datetime.now(timezone.utc)

    session = Session(
        session_id="S001",
        created_at=created_at,
        metadata={
            "user": "test-user",
            "application": "investment-research",
        },
    )

    state = session.snapshot()

    assert isinstance(state, SessionState)
    assert state.session_id == "S001"
    assert state.created_at == created_at
    assert state.metadata == {
        "user": "test-user",
        "application": "investment-research",
    }


def test_session_snapshot_does_not_share_metadata() -> None:
    session = Session(
        session_id="S001",
        created_at=datetime.now(timezone.utc),
        metadata={"key": "value"},
    )

    state = session.snapshot()

    state.metadata["key"] = "changed"

    assert session.metadata["key"] == "value"


def test_session_from_state_reconstructs_session() -> None:
    created_at = datetime.now(timezone.utc)

    state = SessionState(
        session_id="S001",
        created_at=created_at,
        metadata={"application": "investment-research"},
    )

    session = Session.from_state(state)

    assert session.session_id == "S001"
    assert session.created_at == created_at
    assert session.metadata == {
        "application": "investment-research",
    }


def test_session_from_state_does_not_share_metadata() -> None:
    state = SessionState(
        session_id="S001",
        created_at=datetime.now(timezone.utc),
        metadata={"key": "value"},
    )

    session = Session.from_state(state)

    session.metadata["key"] = "changed"

    assert state.metadata["key"] == "value"


def test_session_state_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SessionState(
            session_id="S001",
            created_at=datetime.now(timezone.utc),
            unknown_field="value",
        )