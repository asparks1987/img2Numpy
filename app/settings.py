from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    api_keys: tuple[str, ...]
    api_port: int
    artifact_dir: Path
    artifact_ttl_seconds: int
    max_upload_bytes: int
    max_batch_files: int
    max_process_seconds: int
    max_artifact_bytes: int


def _parse_api_keys(value: str | None) -> tuple[str, ...]:
    if not value:
        return ("dev-local-key",)
    keys = tuple(key.strip() for key in value.split(",") if key.strip())
    return keys or ("dev-local-key",)


def _as_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def get_settings() -> Settings:
    root_dir = Path(__file__).resolve().parent.parent
    artifact_dir = Path(os.getenv("IMG2NUMPY_ARTIFACT_DIR", root_dir / "artifacts")).resolve()
    return Settings(
        api_keys=_parse_api_keys(os.getenv("IMG2NUMPY_API_KEYS")),
        api_port=_as_int("IMG2NUMPY_API_PORT", 8585),
        artifact_dir=artifact_dir,
        artifact_ttl_seconds=_as_int("IMG2NUMPY_ARTIFACT_TTL_SECONDS", 3600),
        max_upload_bytes=_as_int("IMG2NUMPY_MAX_UPLOAD_BYTES", 50 * 1024 * 1024),
        max_batch_files=_as_int("IMG2NUMPY_MAX_BATCH_FILES", 250),
        max_process_seconds=_as_int("IMG2NUMPY_MAX_PROCESS_SECONDS", 120),
        max_artifact_bytes=_as_int("IMG2NUMPY_MAX_ARTIFACT_BYTES", 1024 * 1024 * 1024),
    )
