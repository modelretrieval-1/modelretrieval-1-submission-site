from app.sessions import create_session_value, parse_session_value


def test_session_round_trip():
    value = create_session_value("secret", role="team", account_id=42)

    session = parse_session_value("secret", value)

    assert session is not None
    assert session.role == "team"
    assert session.id == 42


def test_session_rejects_tampered_value():
    value = create_session_value("secret", role="organizer", account_id=1)
    tampered = value.replace("organizer", "team")

    assert parse_session_value("secret", tampered) is None


def test_session_rejects_wrong_secret():
    value = create_session_value("secret", role="team", account_id=42)

    assert parse_session_value("other-secret", value) is None
