from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


OutputMode = Literal["npz", "link"]
NormalizeMode = Literal["none", "0..1", "-1..1"]
ChannelMode = Literal["RGB", "RGBA", "L"]


class ConversionCommandRequest(BaseModel):
    output_mode: OutputMode = "npz"
    dtype: str | None = None
    normalize_mode: NormalizeMode = "none"
    channel_mode: ChannelMode | None = None
    flatten: bool = False
    metadata_only: bool = False


class BatchCommandRequest(ConversionCommandRequest):
    fail_fast: bool = False


class FileResult(BaseModel):
    filename: str
    status: Literal["ok", "error"]
    shape: list[int] | None = None
    dtype: str | None = None
    artifact_key: str | None = None
    error: str | None = None


class ArtifactResponse(BaseModel):
    artifact_id: str
    filename: str
    content_type: str = "application/octet-stream"
    size_bytes: int = Field(..., ge=0)
    created_at: str
    expires_at: str
    download_url: str
