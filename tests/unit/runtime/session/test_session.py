from datetime import datetime, timezone

from runtime.session.session import Session


def test_session_contains_session_id():
    session = Session(
        session_id="session-1"
    )

    assert session.session_id == "session-1"


def test_session_creates_timestamp():
    before = datetime.now(timezone.utc)

    session = Session(
        session_id="session-1"
    )

    after = datetime.now(timezone.utc)

    assert before <= session.created_at <= after


def test_session_metadata_defaults_to_empty_dict():
    session = Session(
        session_id="session-1"
    )

    assert session.metadata == {}


def test_session_metadata_is_supported():
    session = Session(
        session_id="session-1",
        metadata={
            "user": "test-user",
            "channel": "api",
        },
    )

    assert session.metadata == {
        "user": "test-user",
        "channel": "api",
    }


def test_session_metadata_is_not_shared_between_instances():
    session_1 = Session(
        session_id="session-1"
    )

    session_2 = Session(
        session_id="session-2"
    )

    session_1.metadata["key"] = "value"

    assert session_1.metadata == {
        "key": "value"
    }

    assert session_2.metadata == {}