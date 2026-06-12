from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
from typing import Any


BASE_FORMATS = (
    {"format": "PNG", "mime": ("image/png",), "extensions": (".png",), "backend": "pillow"},
    {"format": "JPEG", "mime": ("image/jpeg",), "extensions": (".jpg", ".jpeg"), "backend": "pillow"},
    {"format": "WEBP", "mime": ("image/webp",), "extensions": (".webp",), "backend": "pillow"},
    {"format": "GIF", "mime": ("image/gif",), "extensions": (".gif",), "backend": "pillow"},
    {"format": "BMP", "mime": ("image/bmp",), "extensions": (".bmp",), "backend": "pillow"},
    {"format": "TIFF", "mime": ("image/tiff",), "extensions": (".tif", ".tiff"), "backend": "pillow"},
)

OPTIONAL_FORMATS = (
    {"format": "HEIF", "mime": ("image/heif", "image/heic"), "extensions": (".heif", ".heic"), "extra": "heif"},
    {"format": "AVIF", "mime": ("image/avif",), "extensions": (".avif",), "extra": "avif"},
    {"format": "SVG", "mime": ("image/svg+xml",), "extensions": (".svg",), "extra": "svg"},
    {"format": "PDF", "mime": ("application/pdf",), "extensions": (".pdf",), "extra": "pdf"},
    {"format": "RAW", "mime": ("image/x-raw",), "extensions": (".arw", ".cr2", ".dng", ".nef", ".orf", ".rw2"), "extra": "raw"},
)


def decoder_capabilities() -> dict[str, Any]:
    return {
        "pillow": {"available": True, "backend": "pillow"},
        "heif": {"available": find_spec("pillow_heif") is not None, "backend": "pillow_heif"},
        "avif": {"available": find_spec("pillow_heif") is not None, "backend": "pillow_heif"},
        "svg": {"available": find_spec("cairosvg") is not None, "backend": "cairosvg"},
        "pdf": {"available": find_spec("fitz") is not None or find_spec("pymupdf") is not None, "backend": "pymupdf"},
        "raw": {"available": find_spec("rawpy") is not None, "backend": "rawpy"},
    }


def supported_formats() -> list[dict[str, Any]]:
    capabilities = decoder_capabilities()
    supported: list[dict[str, Any]] = []
    for item in BASE_FORMATS:
        supported.append(
            {
                "format": item["format"],
                "mime": list(item["mime"]),
                "extensions": list(item["extensions"]),
                "available": True,
                "backend": item["backend"],
            }
        )
    for item in OPTIONAL_FORMATS:
        extra = item["extra"]
        supported.append(
            {
                "format": item["format"],
                "mime": list(item["mime"]),
                "extensions": list(item["extensions"]),
                "available": bool(capabilities.get(extra, {}).get("available")),
                "backend": capabilities.get(extra, {}).get("backend", extra),
                "extra": extra,
            }
        )
    return supported


def format_from_extension(path: str | Path) -> str | None:
    suffix = Path(path).suffix.lower()
    for item in BASE_FORMATS + OPTIONAL_FORMATS:
        if suffix in item["extensions"]:
            return item["format"]
    return None

