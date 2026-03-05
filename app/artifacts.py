from __future__ import annotations

import asyncio
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np


@dataclass
class ArtifactMetadata:
    artifact_id: str
    path: Path
    filename: str
    created_at: datetime
    expires_at: datetime
    size_bytes: int
    content_type: str = "application/octet-stream"


class ArtifactStore:
    def __init__(self, base_dir: Path, ttl_seconds: int, max_total_bytes: int = 1024 * 1024 * 1024) -> None:
        self._base_dir = base_dir
        self._ttl_seconds = ttl_seconds
        self._max_total_bytes = max_total_bytes
        self._metadata: dict[str, ArtifactMetadata] = {}
        self._lock = asyncio.Lock()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    async def save_npz(self, arrays: dict[str, np.ndarray], base_name: str, manifest: dict | None = None) -> ArtifactMetadata:
        await self.cleanup_expired()
        artifact_id = secrets.token_urlsafe(18)
        created_at = datetime.now(UTC)
        expires_at = created_at + timedelta(seconds=self._ttl_seconds)
        filename = f"{base_name}.npz"
        output_path = self._base_dir / f"{artifact_id}.npz"

        materialized = dict(arrays)
        if manifest is not None:
            materialized["__manifest_json__"] = np.array(json.dumps(manifest), dtype=np.str_)

        np.savez_compressed(output_path, **materialized)

        size_bytes = output_path.stat().st_size
        async with self._lock:
            current_total = sum(item.size_bytes for item in self._metadata.values())
        if current_total + size_bytes > self._max_total_bytes:
            output_path.unlink(missing_ok=True)
            raise ValueError("Artifact storage limit reached.")

        metadata = ArtifactMetadata(
            artifact_id=artifact_id,
            path=output_path,
            filename=filename,
            created_at=created_at,
            expires_at=expires_at,
            size_bytes=size_bytes,
        )
        async with self._lock:
            self._metadata[artifact_id] = metadata
        return metadata

    async def get(self, artifact_id: str) -> ArtifactMetadata | None:
        await self.cleanup_expired()
        async with self._lock:
            metadata = self._metadata.get(artifact_id)
        if metadata is None:
            return None
        if not metadata.path.exists():
            async with self._lock:
                self._metadata.pop(artifact_id, None)
            return None
        return metadata

    async def cleanup_expired(self) -> None:
        now = datetime.now(UTC)
        async with self._lock:
            expired_ids = [key for key, value in self._metadata.items() if value.expires_at <= now]
            for artifact_id in expired_ids:
                metadata = self._metadata.pop(artifact_id)
                try:
                    metadata.path.unlink(missing_ok=True)
                except OSError:
                    # Best effort cleanup: keep metadata removed so stale links fail fast.
                    pass
