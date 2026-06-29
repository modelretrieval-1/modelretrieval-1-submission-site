from __future__ import annotations

import hmac
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

AccountRole = Literal["organizer", "team"]
SESSION_COOKIE = "modelretrieval_session"


@dataclass(frozen=True)
class SessionAccount:
    role: AccountRole
    id: int


def _signature(secret_key: str, payload: str) -> str:
    return hmac.new(secret_key.encode("utf-8"), payload.encode("utf-8"), sha256).hexdigest()


def create_session_value(secret_key: str, *, role: AccountRole, account_id: int) -> str:
    payload = f"{role}:{account_id}"
    return f"{payload}:{_signature(secret_key, payload)}"


def parse_session_value(secret_key: str, session_value: str | None) -> SessionAccount | None:
    if not session_value:
        return None

    try:
        role, account_id_text, provided_signature = session_value.rsplit(":", 2)
        account_id = int(account_id_text)
    except ValueError:
        return None

    if role not in {"organizer", "team"}:
        return None

    payload = f"{role}:{account_id}"
    expected_signature = _signature(secret_key, payload)
    if not hmac.compare_digest(provided_signature, expected_signature):
        return None

    return SessionAccount(role=role, id=account_id)

