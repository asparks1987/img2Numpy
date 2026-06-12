from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(slots=True)
class ConversionResult:
    source: str
    array: np.ndarray | None
    shape: tuple[int, ...] | None
    dtype: str | None
    format: str | None = None
    mode: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.array is not None


@dataclass(slots=True)
class BatchResult:
    results: list[ConversionResult]

    @property
    def ok_count(self) -> int:
        return sum(1 for item in self.results if item.ok)

    @property
    def error_count(self) -> int:
        return sum(1 for item in self.results if not item.ok)

    @property
    def total_count(self) -> int:
        return len(self.results)

    def arrays(self) -> dict[str, np.ndarray]:
        arrays: dict[str, np.ndarray] = {}
        for idx, item in enumerate(self.results, start=1):
            if item.ok and item.array is not None:
                arrays[_result_key(item, idx)] = item.array
        return arrays


@dataclass(slots=True)
class NPZLoadResult:
    path: Path
    arrays: dict[str, np.ndarray]
    manifest: dict[str, Any] | None = None


def _result_key(result: ConversionResult, index: int) -> str:
    stem = Path(result.source or f"sample_{index}").stem
    safe = "".join(char if char.isalnum() else "_" for char in stem).strip("_")
    return f"{index:04d}_{safe or f'sample_{index}'}"
