from __future__ import annotations

import json
import secrets
import threading
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class APIKeyRecord:
    key_id: str
    client_name: str
    api_key: str
    created_at: str
    last_used_at: str | None = None
    description: str | None = None
    active: bool = True


class APIKeyStore:
    """Persistent API key store for WebUI-generated client profiles."""

    def __init__(self, path: Path, seed_keys: tuple[str, ...]) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._records: list[APIKeyRecord] = []
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load_or_initialize(seed_keys)

    def list_records(self) -> list[APIKeyRecord]:
        with self._lock:
            return [APIKeyRecord(**asdict(record)) for record in self._records]

    def create_key(self, client_name: str, description: str | None = None) -> APIKeyRecord:
        client_name = client_name.strip()
        if not client_name:
            raise ValueError("Client name is required.")

        now = datetime.now(UTC).isoformat()
        record = APIKeyRecord(
            key_id=secrets.token_urlsafe(8),
            client_name=client_name,
            api_key=f"ik_{secrets.token_urlsafe(24)}",
            created_at=now,
            description=description.strip() if description else None,
            active=True,
        )
        with self._lock:
            self._records.append(record)
            self._persist_locked()
        return APIKeyRecord(**asdict(record))

    def revoke_key(self, key_id: str) -> bool:
        with self._lock:
            for record in self._records:
                if record.key_id == key_id and record.active:
                    record.active = False
                    self._persist_locked()
                    return True
        return False

    def validate_and_mark_used(self, api_key: str) -> bool:
        with self._lock:
            for record in self._records:
                if record.active and secrets.compare_digest(record.api_key, api_key):
                    record.last_used_at = datetime.now(UTC).isoformat()
                    self._persist_locked()
                    return True
        return False

    def _load_or_initialize(self, seed_keys: tuple[str, ...]) -> None:
        if self._path.exists():
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            entries = payload.get("api_keys", [])
            self._records = [APIKeyRecord(**entry) for entry in entries]
            return

        now = datetime.now(UTC).isoformat()
        self._records = [
            APIKeyRecord(
                key_id=f"seed_{idx}",
                client_name=f"seed-client-{idx}",
                api_key=key,
                created_at=now,
                description="Seeded from IMG2NUMPY_API_KEYS",
                active=True,
            )
            for idx, key in enumerate(seed_keys, start=1)
        ]
        self._persist_locked()

    def _persist_locked(self) -> None:
        payload = {"api_keys": [asdict(record) for record in self._records]}
        temp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_path.replace(self._path)
