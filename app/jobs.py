from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from typing import Any

import httpx

from app.api_models import BatchCommandRequest
from app.artifacts import ArtifactStore
from app.converter import ConversionOptions, image_bytes_to_array


@dataclass
class PreparedUpload:
    filename: str
    content_type: str
    content: bytes
    ingest_timestamp: str


@dataclass
class JobRecord:
    job_id: str
    status: str
    created_at: str
    output_mode: str
    options: dict[str, Any]
    callback_url: str | None = None
    callback_status: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    results: list[dict[str, Any]] = field(default_factory=list)
    manifest: dict[str, Any] | None = None
    artifact_id: str | None = None
    artifact_filename: str | None = None
    artifact_size_bytes: int | None = None
    artifact_sha256: str | None = None
    stats: dict[str, Any] | None = None
    _task: asyncio.Task | None = field(default=None, repr=False, compare=False)


class JobManager:
    def __init__(
        self,
        artifact_store: ArtifactStore,
        app_version: str,
        schema_version: str,
        max_process_seconds: int,
    ) -> None:
        self._artifact_store = artifact_store
        self._app_version = app_version
        self._schema_version = schema_version
        self._max_process_seconds = max_process_seconds
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def submit_job(
        self,
        job_id: str,
        uploads: list[PreparedUpload],
        request_model: BatchCommandRequest,
        metadata_payload: dict[str, Any],
        callback_url: str | None,
    ) -> JobRecord:
        job = JobRecord(
            job_id=job_id,
            status="queued",
            created_at=datetime.now(UTC).isoformat(),
            output_mode=request_model.output_mode,
            options={
                "dtype": request_model.dtype,
                "normalize_mode": request_model.normalize_mode,
                "channel_mode": request_model.channel_mode,
                "flatten": request_model.flatten,
                "metadata_only": request_model.metadata_only,
                "fail_fast": request_model.fail_fast,
            },
            callback_url=callback_url,
            callback_status="pending" if callback_url else None,
        )
        async with self._lock:
            self._jobs[job_id] = job

        job._task = asyncio.create_task(
            self._run_job(
                job_id=job_id,
                uploads=uploads,
                request_model=request_model,
                metadata_payload=metadata_payload,
            )
        )
        return job

    async def get_job(self, job_id: str) -> JobRecord | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def get_manifest(self, job_id: str) -> dict[str, Any] | None:
        job = await self.get_job(job_id)
        if job is None:
            return None
        return job.manifest

    async def get_stats(self, job_id: str) -> dict[str, Any] | None:
        job = await self.get_job(job_id)
        if job is None:
            return None
        return job.stats

    async def _run_job(
        self,
        job_id: str,
        uploads: list[PreparedUpload],
        request_model: BatchCommandRequest,
        metadata_payload: dict[str, Any],
    ) -> None:
        job = await self.get_job(job_id)
        if job is None:
            return

        job.status = "running"
        job.started_at = datetime.now(UTC).isoformat()

        options = ConversionOptions(
            normalize_mode=request_model.normalize_mode,
            channel_mode=request_model.channel_mode,
            dtype=request_model.dtype,
            flatten=request_model.flatten,
        )
        arrays: dict[str, Any] = {}
        started = monotonic()
        results: list[dict[str, Any]] = []
        global_meta = metadata_payload.get("global", {}) if isinstance(metadata_payload.get("global"), dict) else {}
        per_file_meta = (
            metadata_payload.get("per_file", {}) if isinstance(metadata_payload.get("per_file"), dict) else {}
        )

        try:
            for idx, upload in enumerate(uploads, start=1):
                if monotonic() - started > self._max_process_seconds:
                    raise TimeoutError("Job processing exceeded max process time.")

                sample_id = f"{idx:04d}"
                sample_key = f"{sample_id}_{''.join(c if c.isalnum() else '_' for c in upload.filename)}"
                file_meta = per_file_meta.get(upload.filename, {})
                if not isinstance(file_meta, dict):
                    file_meta = {}
                merged_meta = dict(global_meta)
                merged_meta.update(file_meta)

                source_sha256 = hashlib.sha256(upload.content).hexdigest()
                provenance = {
                    "job_id": job_id,
                    "source_filename": upload.filename,
                    "source_sha256": source_sha256,
                    "ingest_timestamp": upload.ingest_timestamp,
                }

                try:
                    array = image_bytes_to_array(upload.content, options=options)
                    if not request_model.metadata_only:
                        arrays[sample_key] = array
                    result_entry = {
                        "sample_id": sample_id,
                        "artifact_key": sample_key,
                        "filename": upload.filename,
                        "status": "ok",
                        "shape": list(array.shape),
                        "dtype": str(array.dtype),
                        "metadata": merged_meta,
                        "provenance": provenance,
                    }
                    results.append(result_entry)
                except Exception as exc:
                    results.append(
                        {
                            "sample_id": sample_id,
                            "artifact_key": sample_key,
                            "filename": upload.filename,
                            "status": "error",
                            "error": str(exc),
                            "metadata": merged_meta,
                            "provenance": provenance,
                        }
                    )
                    if request_model.fail_fast:
                        break

            ok_results = [item for item in results if item["status"] == "ok"]
            if not ok_results:
                job.status = "failed"
                job.error = "No files were converted successfully."
                job.results = results
                job.finished_at = datetime.now(UTC).isoformat()
                job.manifest = self._build_manifest(job, results)
                job.stats = self._build_stats(results)
                await self._send_callback(job)
                return

            job.results = results
            job.stats = self._build_stats(results)

            if not request_model.metadata_only:
                artifact = await self._artifact_store.save_npz(
                    arrays=arrays,
                    base_name=f"job_{job_id}",
                    manifest={
                        "schema_version": self._schema_version,
                        "converter_version": self._app_version,
                        "job_id": job.job_id,
                        "results": results,
                    },
                )
                job.artifact_id = artifact.artifact_id
                job.artifact_filename = artifact.filename
                job.artifact_size_bytes = artifact.size_bytes
                job.artifact_sha256 = _sha256_file(artifact.path)

            job.finished_at = datetime.now(UTC).isoformat()
            job.status = "done"
            job.manifest = self._build_manifest(job, results)
            await self._send_callback(job)
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = datetime.now(UTC).isoformat()
            await self._send_callback(job)

    def _build_manifest(self, job: JobRecord, results: list[dict[str, Any]]) -> dict[str, Any]:
        ok_count = sum(1 for item in results if item["status"] == "ok")
        error_count = len(results) - ok_count
        return {
            "schema_version": self._schema_version,
            "converter_version": self._app_version,
            "job_id": job.job_id,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "status": job.status,
            "output_mode": job.output_mode,
            "options": job.options,
            "files_total": len(results),
            "ok_count": ok_count,
            "error_count": error_count,
            "artifact_id": job.artifact_id,
            "artifact_sha256": job.artifact_sha256,
            "results": results,
        }

    def _build_stats(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        shape_distribution: dict[str, int] = {}
        class_counts: dict[str, int] = {}
        split_counts: dict[str, int] = {}
        missing_labels = 0
        invalid_count = 0

        for entry in results:
            if entry["status"] != "ok":
                invalid_count += 1
                continue

            shape_key = str(entry.get("shape"))
            shape_distribution[shape_key] = shape_distribution.get(shape_key, 0) + 1

            metadata = entry.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            label = metadata.get("label")
            split = metadata.get("split")

            if label is None:
                missing_labels += 1
            else:
                label_key = str(label)
                class_counts[label_key] = class_counts.get(label_key, 0) + 1

            if split is not None:
                split_key = str(split)
                split_counts[split_key] = split_counts.get(split_key, 0) + 1

        return {
            "shape_distribution": shape_distribution,
            "class_counts": class_counts,
            "split_counts": split_counts,
            "missing_labels": missing_labels,
            "invalid_sample_count": invalid_count,
            "valid_sample_count": len(results) - invalid_count,
            "total_sample_count": len(results),
        }

    async def _send_callback(self, job: JobRecord) -> None:
        if not job.callback_url:
            return

        payload = {
            "job_id": job.job_id,
            "status": job.status,
            "error": job.error,
            "manifest": job.manifest,
            "stats": job.stats,
            "artifact_id": job.artifact_id,
            "artifact_sha256": job.artifact_sha256,
        }
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.post(job.callback_url, json=payload)
            job.callback_status = f"sent:{response.status_code}"
        except Exception as exc:
            job.callback_status = f"failed:{exc}"


def _sha256_file(path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
