from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from app.artifacts import ArtifactStore


def test_artifact_store_save_get_and_cleanup(tmp_path: Path):
    store = ArtifactStore(base_dir=tmp_path, ttl_seconds=1)
    payload = {"sample_0001": np.array([1, 2, 3])}
    metadata = asyncio.run(store.save_npz(payload, base_name="sample"))

    fetched = asyncio.run(store.get(metadata.artifact_id))
    assert fetched is not None
    assert fetched.path.exists()
    assert fetched.size_bytes > 0

    store_short_ttl = ArtifactStore(base_dir=tmp_path, ttl_seconds=0)
    expired = asyncio.run(store_short_ttl.save_npz(payload, base_name="expired"))
    asyncio.run(store_short_ttl.cleanup_expired())
    assert asyncio.run(store_short_ttl.get(expired.artifact_id)) is None


def test_artifact_store_enforces_storage_limit(tmp_path: Path):
    store = ArtifactStore(base_dir=tmp_path, ttl_seconds=60, max_total_bytes=50)
    payload = {"sample_0001": np.arange(100)}
    try:
        asyncio.run(store.save_npz(payload, base_name="limited"))
    except ValueError as exc:
        assert "storage limit reached" in str(exc).lower()
    else:
        raise AssertionError("Expected storage limit error")
