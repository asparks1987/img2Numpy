from __future__ import annotations

import json
from dataclasses import dataclass
import mimetypes
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Mapping

import httpx

from .exceptions import APIClientError, APIResponseError
from .options import ConversionOptions


@dataclass(slots=True)
class _UploadPart:
    name: str
    filename: str
    content: bytes
    content_type: str


class Img2NumpyClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def _request(self, method: str, path: str, *, files: Any = None, data: Mapping[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        try:
            response = httpx.request(method, url, files=files, data=data, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise APIClientError(str(exc)) from exc
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise APIResponseError(f"{response.status_code} response from img2numpy API: {detail}")
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response.content

    def _options_to_fields(self, options: ConversionOptions | None) -> dict[str, Any]:
        options = options or ConversionOptions()
        fields: dict[str, Any] = {"output_mode": "link"}
        if options.dtype is not None:
            fields["dtype"] = options.dtype
        if options.normalize_mode is not None:
            fields["normalize_mode"] = options.normalize_mode
        if options.channel_mode is not None:
            fields["channel_mode"] = options.channel_mode
        if options.flatten:
            fields["flatten"] = "true"
        return fields

    def _source_to_upload(self, source: Any, index: int = 1) -> _UploadPart:
        if isinstance(source, (bytes, bytearray, memoryview)):
            return _UploadPart("file", f"sample_{index}.bin", bytes(source), "application/octet-stream")
        if isinstance(source, (str, Path)):
            path = Path(source)
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            return _UploadPart("file", path.name, path.read_bytes(), content_type)
        if hasattr(source, "read") and callable(source.read):
            payload = source.read()
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            return _UploadPart("file", getattr(source, "name", f"sample_{index}.bin"), bytes(payload), "application/octet-stream")
        raise APIClientError(f"Unsupported upload source: {type(source).__name__}")

    def _iter_sources(self, sources: Any) -> Iterable[Any]:
        if isinstance(sources, (bytes, bytearray, memoryview, str, Path)):
            return [sources]
        if hasattr(sources, "read") and callable(sources.read):
            return [sources]
        if isinstance(sources, Iterable):
            return sources
        return [sources]

    def convert(self, source: Any, options: ConversionOptions | None = None, output_mode: str = "link") -> Any:
        upload = self._source_to_upload(source)
        data = self._options_to_fields(options)
        data["output_mode"] = output_mode
        return self._request(
            "POST",
            f"/api/v1/{self._api_key}/convert",
            files=[(upload.name, (upload.filename, upload.content, upload.content_type))],
            data=data,
        )

    def batch(self, sources: Any, options: ConversionOptions | None = None, fail_fast: bool = False, output_mode: str = "link") -> Any:
        files = []
        for index, source in enumerate(self._iter_sources(sources), start=1):
            upload = self._source_to_upload(source, index=index)
            files.append((f"files", (upload.filename, upload.content, upload.content_type)))
        data = self._options_to_fields(options)
        data["output_mode"] = output_mode
        data["fail_fast"] = "true" if fail_fast else "false"
        return self._request("POST", f"/api/v1/{self._api_key}/batch", files=files, data=data)

    def submit_job(
        self,
        sources: Any,
        options: ConversionOptions | None = None,
        metadata: dict[str, Any] | None = None,
        callback_url: str | None = None,
    ) -> Any:
        files = []
        for index, source in enumerate(self._iter_sources(sources), start=1):
            upload = self._source_to_upload(source, index=index)
            files.append(("files", (upload.filename, upload.content, upload.content_type)))
        data = self._options_to_fields(options)
        if metadata is not None:
            data["metadata_json"] = json.dumps(metadata)
        if callback_url is not None:
            data["callback_url"] = callback_url
        return self._request("POST", f"/api/v1/{self._api_key}/jobs/submit", files=files, data=data)

    def get_job(self, job_id: str) -> Any:
        return self._request("GET", f"/api/v1/{self._api_key}/jobs/{job_id}")

    def get_manifest(self, job_id: str) -> Any:
        return self._request("GET", f"/api/v1/{self._api_key}/jobs/{job_id}/manifest")

    def get_stats(self, job_id: str) -> Any:
        return self._request("GET", f"/api/v1/{self._api_key}/jobs/{job_id}/stats")

    def download_artifact(self, artifact_id: str, path: str | Path | None = None) -> bytes | Path:
        data = self._request("GET", f"/api/v1/{self._api_key}/download/{artifact_id}")
        if path is None:
            return data
        output_path = Path(path)
        output_path.write_bytes(data)
        return output_path
