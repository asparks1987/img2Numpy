from __future__ import annotations

import asyncio
import base64
import json
import secrets
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.api_models import ArtifactResponse, BatchCommandRequest, ConversionCommandRequest, FileResult
from app.artifacts import ArtifactStore
from app.converter import ConversionOptions, image_bytes_to_array
from app.jobs import JobManager, PreparedUpload
from app.key_store import APIKeyStore
from app.settings import get_settings

app = FastAPI(title="img2numpy", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
settings = get_settings()
artifact_store = ArtifactStore(
    settings.artifact_dir,
    settings.artifact_ttl_seconds,
    max_total_bytes=settings.max_artifact_bytes,
)
api_key_store = APIKeyStore(settings.api_key_store_path, settings.api_keys)
job_manager = JobManager(
    artifact_store=artifact_store,
    app_version=app.version,
    schema_version="img2numpy.job_manifest.v1",
    max_process_seconds=settings.max_process_seconds,
)
cleanup_task: asyncio.Task | None = None

SUPPORTED_IMAGE_MATRIX = (
    {"format": "PNG", "mime": ("image/png",), "extensions": (".png",)},
    {"format": "JPEG", "mime": ("image/jpeg",), "extensions": (".jpg", ".jpeg")},
    {"format": "WEBP", "mime": ("image/webp",), "extensions": (".webp",)},
    {"format": "GIF", "mime": ("image/gif",), "extensions": (".gif",)},
    {"format": "BMP", "mime": ("image/bmp",), "extensions": (".bmp",)},
    {"format": "TIFF", "mime": ("image/tiff",), "extensions": (".tif", ".tiff")},
)


def _sanitize_npz_key(name: str, index: int) -> str:
    stem = Path(name or f"sample_{index}").stem
    safe = "".join(char if char.isalnum() else "_" for char in stem).strip("_")
    if not safe:
        safe = f"sample_{index}"
    return f"{index:04d}_{safe}"


async def _read_upload_file(upload: UploadFile) -> bytes:
    chunk_size = 1024 * 1024
    total = 0
    chunks: list[bytes] = []
    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File '{upload.filename}' exceeds max upload size of {settings.max_upload_bytes} bytes.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _build_conversion_options(request_model: ConversionCommandRequest) -> ConversionOptions:
    return ConversionOptions(
        normalize_mode=request_model.normalize_mode,
        channel_mode=request_model.channel_mode,
        dtype=request_model.dtype,
        flatten=request_model.flatten,
    )


def _artifact_response(metadata, request: Request, api_key: str) -> ArtifactResponse:
    return ArtifactResponse(
        artifact_id=metadata.artifact_id,
        filename=metadata.filename,
        size_bytes=metadata.size_bytes,
        created_at=metadata.created_at.astimezone(UTC).isoformat(),
        expires_at=metadata.expires_at.astimezone(UTC).isoformat(),
        download_url=str(request.url_for("download_artifact", api_key=api_key, artifact_id=metadata.artifact_id)),
    )


def _parse_metadata_payload(raw_value: str | None) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid metadata_json payload: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="metadata_json must be a JSON object.")
    return parsed


def _validate_api_key_or_401(api_key: str) -> None:
    if not api_key_store.validate_and_mark_used(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key.")


def _default_ui_api_key() -> str:
    for record in api_key_store.list_records():
        if record.active:
            return record.api_key
    generated = api_key_store.create_key("webui-default")
    return generated.api_key


def _ui_context(
    result: dict[str, Any] | None = None,
    error: str | None = None,
    key_message: str | None = None,
    key_error: str | None = None,
    new_api_key: str | None = None,
) -> dict[str, Any]:
    return {
        "result": result,
        "error": error,
        "key_message": key_message,
        "key_error": key_error,
        "new_api_key": new_api_key,
        "api_keys": api_key_store.list_records(),
    }


async def _stream_artifact(metadata: ArtifactResponse, path: Path) -> FileResponse:
    response = FileResponse(
        path=path,
        filename=metadata.filename,
        media_type=metadata.content_type,
    )
    response.headers["X-Artifact-Id"] = metadata.artifact_id
    response.headers["X-Artifact-Expires-At"] = metadata.expires_at
    return response


async def _handle_convert_command(
    request: Request,
    api_key: str,
    file: UploadFile | None,
    files: list[UploadFile] | None,
    request_model: ConversionCommandRequest,
):
    selected_file: UploadFile | None = file
    if selected_file is None and files:
        selected_file = files[0]
    if selected_file is None:
        raise HTTPException(status_code=400, detail="Convert command requires 'file'.")

    content = await _read_upload_file(selected_file)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        options = _build_conversion_options(request_model)
        array = image_bytes_to_array(content, options=options)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not process image: {exc}") from exc

    result = FileResult(
        filename=selected_file.filename or "uploaded_image",
        status="ok",
        shape=list(array.shape),
        dtype=str(array.dtype),
        artifact_key="0001_input",
    )
    if request_model.metadata_only:
        return {"command": "convert", "result": result.model_dump()}

    manifest = {
        "command": "convert",
        "output_mode": request_model.output_mode,
        "results": [result.model_dump()],
    }
    try:
        artifact = await artifact_store.save_npz(
            arrays={"0001_input": array},
            base_name=Path(selected_file.filename or "converted").stem,
            manifest=manifest,
        )
    except ValueError as exc:
        raise HTTPException(status_code=507, detail=str(exc)) from exc
    payload = _artifact_response(artifact, request, api_key)

    if request_model.output_mode == "link":
        return {
            "command": "convert",
            "artifact": payload.model_dump(),
            "result": result.model_dump(),
        }
    return await _stream_artifact(payload, artifact.path)


async def _handle_batch_command(
    request: Request,
    api_key: str,
    file: UploadFile | None,
    files: list[UploadFile] | None,
    request_model: BatchCommandRequest,
):
    batch_files: list[UploadFile] = []
    if files:
        batch_files.extend(files)
    if file is not None:
        batch_files.append(file)
    if not batch_files:
        raise HTTPException(status_code=400, detail="Batch command requires 'files'.")
    if len(batch_files) > settings.max_batch_files:
        raise HTTPException(
            status_code=413,
            detail=f"Batch exceeds max file count of {settings.max_batch_files}.",
        )

    conversion_options = _build_conversion_options(request_model)
    array_entries: dict[str, object] = {}
    results: list[FileResult] = []
    started = time.monotonic()
    for idx, upload in enumerate(batch_files, start=1):
        if time.monotonic() - started > settings.max_process_seconds:
            raise HTTPException(status_code=408, detail="Batch processing exceeded max process time.")
        key = _sanitize_npz_key(upload.filename or f"file_{idx}", idx)
        try:
            content = await _read_upload_file(upload)
            if not content:
                raise ValueError("Uploaded file is empty.")
            array = image_bytes_to_array(content, options=conversion_options)
            if not request_model.metadata_only:
                array_entries[key] = array
            results.append(
                FileResult(
                    filename=upload.filename or f"file_{idx}",
                    status="ok",
                    shape=list(array.shape),
                    dtype=str(array.dtype),
                    artifact_key=key,
                )
            )
        except Exception as exc:
            results.append(
                FileResult(
                    filename=upload.filename or f"file_{idx}",
                    status="error",
                    error=str(exc),
                )
            )
            if request_model.fail_fast:
                break

    if not any(item.status == "ok" for item in results):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No files were converted successfully.",
                "results": [item.model_dump() for item in results],
            },
        )

    if request_model.metadata_only:
        return {
            "command": "batch",
            "results": [item.model_dump() for item in results],
        }

    manifest = {
        "command": "batch",
        "output_mode": request_model.output_mode,
        "result_count": len(results),
        "results": [item.model_dump() for item in results],
    }
    try:
        artifact = await artifact_store.save_npz(
            arrays=array_entries,
            base_name="batch_conversion",
            manifest=manifest,
        )
    except ValueError as exc:
        raise HTTPException(status_code=507, detail=str(exc)) from exc
    payload = _artifact_response(artifact, request, api_key)

    if request_model.output_mode == "link":
        return {
            "command": "batch",
            "artifact": payload.model_dump(),
            "results": [item.model_dump() for item in results],
        }

    return await _stream_artifact(payload, artifact.path)


async def _handle_download_command(artifact_id: str | None, api_key: str):
    if not artifact_id:
        raise HTTPException(status_code=400, detail="Download command requires 'artifact_id'.")
    metadata = await artifact_store.get(artifact_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Artifact not found or expired.")
    response_payload = ArtifactResponse(
        artifact_id=metadata.artifact_id,
        filename=metadata.filename,
        size_bytes=metadata.size_bytes,
        created_at=metadata.created_at.astimezone(UTC).isoformat(),
        expires_at=metadata.expires_at.astimezone(UTC).isoformat(),
        download_url="",
    )
    return await _stream_artifact(response_payload, metadata.path)


async def _cleanup_worker() -> None:
    while True:
        await artifact_store.cleanup_expired()
        await asyncio.sleep(60)


@app.on_event("startup")
async def on_startup() -> None:
    global cleanup_task
    cleanup_task = asyncio.create_task(_cleanup_worker())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global cleanup_task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/formats")
def supported_formats() -> dict[str, object]:
    return {"supported": SUPPORTED_IMAGE_MATRIX}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=_ui_context(),
    )


@app.post("/keys/generate", response_class=HTMLResponse)
async def generate_api_key(
    request: Request,
    client_name: str = Form(...),
    description: str | None = Form(None),
):
    try:
        generated = api_key_store.create_key(client_name=client_name, description=description)
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_ui_context(
                key_message=f"Generated API key for client profile '{generated.client_name}'.",
                new_api_key=generated.api_key,
            ),
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_ui_context(key_error=str(exc)),
            status_code=400,
        )


@app.post("/keys/revoke", response_class=HTMLResponse)
async def revoke_api_key(request: Request, key_id: str = Form(...)):
    revoked = api_key_store.revoke_key(key_id)
    if not revoked:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_ui_context(key_error="Could not revoke key (not found or already inactive)."),
            status_code=400,
        )
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=_ui_context(key_message=f"Revoked API key profile: {key_id}"),
    )


@app.post("/", response_class=HTMLResponse)
async def convert_form(
    request: Request,
):
    form = await request.form()
    raw_file = form.get("file")
    raw_files = form.getlist("files")
    output_mode = str(form.get("output_mode", "npz"))
    dtype = form.get("dtype")
    normalize_mode = str(form.get("normalize_mode", "none"))
    channel_mode = form.get("channel_mode")
    flatten = str(form.get("flatten", "false")).lower() in {"1", "true", "yes", "on"}
    metadata_only = str(form.get("metadata_only", "false")).lower() in {"1", "true", "yes", "on"}
    fail_fast = str(form.get("fail_fast", "false")).lower() in {"1", "true", "yes", "on"}

    selected_files: list[UploadFile] = []
    selected_files.extend(item for item in raw_files if hasattr(item, "read"))
    if raw_file is not None and hasattr(raw_file, "read"):
        selected_files.append(raw_file)
    if not selected_files:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_ui_context(error="Upload at least one image file."),
            status_code=400,
        )

    command_name = "batch" if len(selected_files) > 1 else "convert"
    try:
        if command_name == "batch":
            request_model: BatchCommandRequest | ConversionCommandRequest = BatchCommandRequest(
                output_mode=output_mode,
                dtype=dtype,
                normalize_mode=normalize_mode,
                channel_mode=channel_mode,
                flatten=flatten,
                metadata_only=metadata_only,
                fail_fast=fail_fast,
            )
        else:
            request_model = ConversionCommandRequest(
                output_mode=output_mode,
                dtype=dtype,
                normalize_mode=normalize_mode,
                channel_mode=channel_mode,
                flatten=flatten,
                metadata_only=metadata_only,
            )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_ui_context(error=f"Invalid form options: {exc}"),
            status_code=400,
        )

    options = _build_conversion_options(request_model)
    arrays: dict[str, object] = {}
    results: list[dict[str, Any]] = []
    preview_entry: dict[str, Any] | None = None
    started = time.monotonic()

    for idx, upload in enumerate(selected_files, start=1):
        if time.monotonic() - started > settings.max_process_seconds:
            return templates.TemplateResponse(
                request=request,
                name="index.html",
                context=_ui_context(error=f"Processing exceeded max time ({settings.max_process_seconds}s)."),
                status_code=408,
            )
        sample_key = _sanitize_npz_key(upload.filename or f"file_{idx}", idx)
        try:
            content = await _read_upload_file(upload)
            if not content:
                raise ValueError("Uploaded file is empty.")
            array = image_bytes_to_array(content, options=options)
            if not request_model.metadata_only:
                arrays[sample_key] = array
            result_item = {
                "filename": upload.filename or f"file_{idx}",
                "status": "ok",
                "shape": list(array.shape),
                "dtype": str(array.dtype),
                "artifact_key": sample_key,
                "error": None,
            }
            results.append(result_item)
            if preview_entry is None:
                preview_entry = {
                    "filename": upload.filename or f"file_{idx}",
                    "mime_type": upload.content_type or "image/*",
                    "preview_bytes": base64.b64encode(content).decode("utf-8"),
                    "array_preview": array.tolist()[:20],
                    "shape": list(array.shape),
                    "dtype": str(array.dtype),
                }
        except Exception as exc:
            results.append(
                {
                    "filename": upload.filename or f"file_{idx}",
                    "status": "error",
                    "shape": None,
                    "dtype": None,
                    "artifact_key": sample_key,
                    "error": str(exc),
                }
            )
            if isinstance(request_model, BatchCommandRequest) and request_model.fail_fast:
                break

    ok_count = sum(1 for entry in results if entry["status"] == "ok")
    if ok_count == 0:
        result = {
            "command": command_name,
            "output_mode": request_model.output_mode,
            "metadata_only": request_model.metadata_only,
            "fail_fast": bool(getattr(request_model, "fail_fast", False)),
            "total_files": len(selected_files),
            "ok_count": 0,
            "error_count": len(results),
            "options": {
                "dtype": request_model.dtype,
                "normalize_mode": request_model.normalize_mode,
                "channel_mode": request_model.channel_mode,
                "flatten": request_model.flatten,
            },
            "artifact": None,
            "preview": None,
            "results": results,
        }
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_ui_context(result=result, error="No files were converted successfully."),
            status_code=400,
        )

    artifact_payload: dict[str, Any] | None = None
    if not request_model.metadata_only:
        try:
            artifact = await artifact_store.save_npz(
                arrays=arrays,
                base_name="ui_conversion",
                manifest={
                    "source": "browser_ui",
                    "command": command_name,
                    "result_count": len(results),
                    "results": results,
                },
            )
        except ValueError as exc:
            return templates.TemplateResponse(
                request=request,
                name="index.html",
                context=_ui_context(error=str(exc)),
                status_code=507,
            )
        artifact_response = _artifact_response(artifact, request, _default_ui_api_key())
        artifact_payload = artifact_response.model_dump()

    result = {
        "command": command_name,
        "output_mode": request_model.output_mode,
        "metadata_only": request_model.metadata_only,
        "fail_fast": bool(getattr(request_model, "fail_fast", False)),
        "total_files": len(selected_files),
        "ok_count": ok_count,
        "error_count": len(results) - ok_count,
        "options": {
            "dtype": request_model.dtype,
            "normalize_mode": request_model.normalize_mode,
            "channel_mode": request_model.channel_mode,
            "flatten": request_model.flatten,
        },
        "artifact": artifact_payload,
        "preview": preview_entry,
        "results": results,
    }
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=_ui_context(result=result),
    )


@app.post("/api/convert")
async def convert_api(
    file: UploadFile = File(...),
    color: bool = Form(True),
    normalize: bool = Form(False),
):
    content = await _read_upload_file(file)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        options = ConversionOptions(color=color, normalize=normalize)
        array = image_bytes_to_array(content, options=options)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not process image: {exc}") from exc

    return {
        "filename": file.filename,
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "array": array.tolist(),
    }


@app.post("/api/v1/{api_key}/{command}")
async def command_router(
    request: Request,
    api_key: str,
    command: str,
):
    _validate_api_key_or_401(api_key)

    form = await request.form()
    raw_file = form.get("file")
    raw_files = form.getlist("files")
    file = raw_file if raw_file is not None and hasattr(raw_file, "read") else None
    files = [item for item in raw_files if hasattr(item, "read")]
    output_mode = str(form.get("output_mode", "npz"))
    dtype = form.get("dtype")
    normalize_mode = str(form.get("normalize_mode", "none"))
    channel_mode = form.get("channel_mode")
    metadata_only = str(form.get("metadata_only", "false")).lower() in {"1", "true", "yes", "on"}
    flatten = str(form.get("flatten", "false")).lower() in {"1", "true", "yes", "on"}
    fail_fast = str(form.get("fail_fast", "false")).lower() in {"1", "true", "yes", "on"}
    artifact_id = form.get("artifact_id")

    handlers = {
        "convert": _handle_convert_command,
        "batch": _handle_batch_command,
        "download": _handle_download_command,
    }
    handler = handlers.get(command)
    if handler is None:
        raise HTTPException(status_code=404, detail=f"Unknown command '{command}'.")

    if command == "download":
        return await _handle_download_command(artifact_id, api_key)

    try:
        if command == "batch":
            request_model = BatchCommandRequest(
                output_mode=output_mode,
                dtype=dtype,
                normalize_mode=normalize_mode,
                channel_mode=channel_mode,
                flatten=flatten,
                metadata_only=metadata_only,
                fail_fast=fail_fast,
            )
            return await _handle_batch_command(request, api_key, file, files, request_model)
        request_model = ConversionCommandRequest(
            output_mode=output_mode,
            dtype=dtype,
            normalize_mode=normalize_mode,
            channel_mode=channel_mode,
            flatten=flatten,
            metadata_only=metadata_only,
        )
        return await _handle_convert_command(request, api_key, file, files, request_model)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc


@app.get("/api/v1/{api_key}/download/{artifact_id}", name="download_artifact")
async def download_artifact(api_key: str, artifact_id: str):
    _validate_api_key_or_401(api_key)
    return await _handle_download_command(artifact_id, api_key)


@app.post("/api/v1/{api_key}/jobs/submit")
async def submit_job(request: Request, api_key: str):
    _validate_api_key_or_401(api_key)

    form = await request.form()
    raw_file = form.get("file")
    raw_files = form.getlist("files")
    files = [item for item in raw_files if hasattr(item, "read")]
    if raw_file is not None and hasattr(raw_file, "read"):
        files.append(raw_file)
    if not files:
        raise HTTPException(status_code=400, detail="Job submission requires at least one file.")

    try:
        request_model = BatchCommandRequest(
            output_mode=str(form.get("output_mode", "npz")),
            dtype=form.get("dtype"),
            normalize_mode=str(form.get("normalize_mode", "none")),
            channel_mode=form.get("channel_mode"),
            flatten=str(form.get("flatten", "false")).lower() in {"1", "true", "yes", "on"},
            metadata_only=str(form.get("metadata_only", "false")).lower() in {"1", "true", "yes", "on"},
            fail_fast=str(form.get("fail_fast", "false")).lower() in {"1", "true", "yes", "on"},
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc

    metadata_payload = _parse_metadata_payload(form.get("metadata_json"))
    callback_url = form.get("callback_url")
    uploads: list[PreparedUpload] = []
    for upload in files:
        payload = await _read_upload_file(upload)
        if not payload:
            continue
        uploads.append(
            PreparedUpload(
                filename=upload.filename or "uploaded_file",
                content_type=upload.content_type or "application/octet-stream",
                content=payload,
                ingest_timestamp=datetime.now(UTC).isoformat(),
            )
        )
    if not uploads:
        raise HTTPException(status_code=400, detail="All uploaded files were empty.")

    job_id = secrets.token_urlsafe(12)
    job = await job_manager.submit_job(
        job_id=job_id,
        uploads=uploads,
        request_model=request_model,
        metadata_payload=metadata_payload,
        callback_url=callback_url,
    )
    return {
        "job_id": job.job_id,
        "status": job.status,
        "status_url": str(request.url_for("get_job_status", api_key=api_key, job_id=job_id)),
        "manifest_url": str(request.url_for("get_job_manifest", api_key=api_key, job_id=job_id)),
        "stats_url": str(request.url_for("get_job_stats", api_key=api_key, job_id=job_id)),
    }


@app.get("/api/v1/{api_key}/jobs/{job_id}", name="get_job_status")
async def get_job_status(request: Request, api_key: str, job_id: str):
    _validate_api_key_or_401(api_key)
    job = await job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    payload = {
        "job_id": job.job_id,
        "status": job.status,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error": job.error,
        "options": job.options,
        "callback_url": job.callback_url,
        "callback_status": job.callback_status,
        "artifact_id": job.artifact_id,
        "artifact_filename": job.artifact_filename,
        "artifact_size_bytes": job.artifact_size_bytes,
        "artifact_sha256": job.artifact_sha256,
        "manifest_url": str(request.url_for("get_job_manifest", api_key=api_key, job_id=job_id)),
        "stats_url": str(request.url_for("get_job_stats", api_key=api_key, job_id=job_id)),
        "result_count": len(job.results),
    }
    if job.artifact_id:
        payload["download_url"] = str(
            request.url_for("download_artifact", api_key=api_key, artifact_id=job.artifact_id)
        )
    return payload


@app.get("/api/v1/{api_key}/jobs/{job_id}/manifest", name="get_job_manifest")
async def get_job_manifest(api_key: str, job_id: str):
    _validate_api_key_or_401(api_key)
    manifest = await job_manager.get_manifest(job_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Manifest not found.")
    return manifest


@app.get("/api/v1/{api_key}/jobs/{job_id}/stats", name="get_job_stats")
async def get_job_stats(api_key: str, job_id: str):
    _validate_api_key_or_401(api_key)
    stats = await job_manager.get_stats(job_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="Stats not found.")
    return stats
