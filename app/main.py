from __future__ import annotations

import asyncio
import base64
import time
from datetime import UTC
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.api_models import ArtifactResponse, BatchCommandRequest, ConversionCommandRequest, FileResult
from app.artifacts import ArtifactStore
from app.auth import is_valid_api_key
from app.converter import ConversionOptions, image_bytes_to_array
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
        context={"result": None, "error": None},
    )


@app.post("/", response_class=HTMLResponse)
async def convert_form(
    request: Request,
    file: UploadFile = File(...),
    color: bool = Form(True),
    normalize: bool = Form(False),
):
    content = await file.read()
    if not content:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"result": None, "error": "Uploaded file is empty."},
            status_code=400,
        )

    try:
        options = ConversionOptions(color=color, normalize=normalize)
        array = image_bytes_to_array(content, options=options)
    except Exception as exc:  # invalid image payload
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"result": None, "error": f"Could not process image: {exc}"},
            status_code=400,
        )

    preview_bytes = base64.b64encode(content).decode("utf-8")
    result = {
        "filename": file.filename,
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "array_preview": array.tolist()[:20],
        "preview_bytes": preview_bytes,
        "mime_type": file.content_type or "image/*",
    }
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"result": result, "error": None},
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
    if not is_valid_api_key(api_key, settings.api_keys):
        raise HTTPException(status_code=401, detail="Invalid API key.")

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
    if not is_valid_api_key(api_key, settings.api_keys):
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return await _handle_download_command(artifact_id, api_key)
