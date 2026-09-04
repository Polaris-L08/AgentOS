import pytest

from runtime.session.session_manager import SessionManager


def test_create_session():
    manager = SessionManager()

    session = manager.create_session()

    assert session.session_id
    assert manager.has_session(
        session.session_id
    )


def test_create_session_with_metadata():
    manager = SessionManager()

    session = manager.create_session(
        metadata={
            "channel": "api"
        }
    )

    assert session.metadata == {
        "channel": "api"
    }


def test_create_sessions_have_unique_ids():
    manager = SessionManager()

    session_1 = manager.create_session()
    session_2 = manager.create_session()

    assert session_1.session_id != session_2.session_id


def test_get_session():
    manager = SessionManager()

    session = manager.create_session()

    result = manager.get_session(
        session.session_id
    )

    assert result is session


def test_get_unknown_session_raises_key_error():
    manager = SessionManager()

    with pytest.raises(KeyError, match="Session not found"):
        manager.get_session("unknown-session")


def test_has_session_returns_true_for_existing_session():
    manager = SessionManager()

    session = manager.create_session()

    assert manager.has_session(
        session.session_id
    ) is True


def test_has_session_returns_false_for_unknown_session():
    manager = SessionManager()

    assert manager.has_session(
        "unknown-session"
    ) is False


def test_delete_session():
    manager = SessionManager()

    session = manager.create_session()

    manager.delete_session(
        session.session_id
    )

    assert manager.has_session(
        session.session_id
    ) is False


def test_delete_unknown_session_raises_key_error():
    manager = SessionManager()

    with pytest.raises(KeyError, match="Session not found"):
        manager.delete_session("unknown-session")


def test_multiple_sessions_are_independent():
    manager = SessionManager()

    session_1 = manager.create_session()
    session_2 = manager.create_session()

    assert manager.get_session(
        session_1.session_id
    ) is session_1

    assert manager.get_session(
        session_2.session_id
    ) is session_2

    manager.delete_session(
        session_1.session_id
    )

    assert manager.has_session(
        session_1.session_id
    ) is False

    assert manager.has_session(
        session_2.session_id
    ) is True