from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Pairing:
    device_id: str
    session_id: str
    token: str
    created_at: int

    def public(self) -> dict[str, str | int]:
        return {
            "device_id": self.device_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
        }


def create_pairing() -> Pairing:
    device_id = "dev_" + secrets.token_urlsafe(12)
    session_id = "ses_" + secrets.token_urlsafe(18)
    token = secrets.token_urlsafe(32)
    return Pairing(device_id, session_id, token, int(time.time()))


def fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def save_pairing(path: str | Path, pairing: Pairing) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "device_id": pairing.device_id,
        "session_id": pairing.session_id,
        "token": pairing.token,
        "created_at": pairing.created_at,
    }, indent=2), encoding="utf-8")
    try:
        p.chmod(0o600)
    except OSError:
        pass
