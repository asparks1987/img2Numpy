from __future__ import annotations

import base64
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.converter import ConversionOptions, image_bytes_to_array

app = FastAPI(title="img2numpy", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    content = await file.read()
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
