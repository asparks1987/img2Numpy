from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .exceptions import NPZError
from .results import BatchResult, ConversionResult, NPZLoadResult


def _manifest_array(manifest: dict[str, Any] | None) -> dict[str, np.ndarray]:
    if manifest is None:
        return {}
    return {"__manifest_json__": np.array(json.dumps(manifest), dtype=np.str_)}


def _default_key(index: int, source: str | None) -> str:
    stem = Path(source or f"sample_{index}").stem
    safe = "".join(char if char.isalnum() else "_" for char in stem).strip("_")
    return f"{index:04d}_{safe or f'sample_{index}'}"


def _coerce_arrays(
    payload: Mapping[str, np.ndarray] | Sequence[ConversionResult] | BatchResult,
) -> dict[str, np.ndarray]:
    if isinstance(payload, BatchResult):
        return payload.arrays()
    if isinstance(payload, Mapping):
        return {str(key): np.asarray(value) for key, value in payload.items()}
    arrays: dict[str, np.ndarray] = {}
    for index, item in enumerate(payload, start=1):
        if item.ok and item.array is not None:
            arrays[_default_key(index, item.source)] = item.array
    return arrays


def save_npz(
    payload: Mapping[str, np.ndarray] | Sequence[ConversionResult] | BatchResult,
    path: str | Path,
    manifest: dict[str, Any] | None = None,
    compressed: bool = True,
) -> Path:
    arrays = _coerce_arrays(payload)
    output_path = Path(path)
    if output_path.suffix.lower() != ".npz":
        output_path = output_path.with_suffix(".npz")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    materialized = dict(arrays)
    materialized.update(_manifest_array(manifest))

    try:
        if compressed:
            np.savez_compressed(output_path, **materialized)
        else:
            np.savez(output_path, **materialized)
    except OSError as exc:
        raise NPZError(f"Failed to write NPZ file: {exc}") from exc
    return output_path


def load_npz(path: str | Path) -> NPZLoadResult:
    input_path = Path(path)
    if not input_path.exists():
        raise NPZError(f"NPZ file does not exist: {input_path}")

    try:
        with np.load(input_path, allow_pickle=True) as payload:
            arrays: dict[str, np.ndarray] = {}
            manifest: dict[str, Any] | None = None
            for key in payload.files:
                if key == "__manifest_json__":
                    raw = payload[key]
                    if raw.shape == ():
                        manifest_json = str(raw.item())
                    else:
                        manifest_json = str(raw.tolist())
                    try:
                        manifest = json.loads(manifest_json)
                    except json.JSONDecodeError:
                        manifest = {"raw": manifest_json}
                    continue
                arrays[key] = payload[key]
    except OSError as exc:
        raise NPZError(f"Failed to read NPZ file: {exc}") from exc

    return NPZLoadResult(path=input_path, arrays=arrays, manifest=manifest)
