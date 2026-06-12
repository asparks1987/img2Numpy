from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


NormalizeMode = Literal["none", "0..1", "-1..1"]
ChannelMode = Literal["RGB", "RGBA", "L", "LA", "CMYK", "P"]
FrameSelection = int | Literal["all"] | None


@dataclass(slots=True)
class ConversionOptions:
    channel_mode: ChannelMode | None = None
    normalize_mode: NormalizeMode = "none"
    dtype: str | None = None
    flatten: bool = False
    frame: FrameSelection = None
    resize: tuple[int, int] | None = None
    preserve_metadata: bool = False
    url_timeout_seconds: float = 15.0

