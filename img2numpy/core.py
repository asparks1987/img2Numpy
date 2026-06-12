from __future__ import annotations

import glob
import importlib.util
import io
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

import numpy as np
from PIL import Image, ImageSequence

from .capabilities import format_from_extension
from .exceptions import ConversionError, UnsupportedFormatError
from .options import ConversionOptions
from .results import BatchResult, ConversionResult


_RAW_EXTENSIONS = {".arw", ".cr2", ".dng", ".nef", ".orf", ".rw2"}


def _is_url(value: str) -> bool:
    return urlparse(value).scheme.lower() in {"http", "https"}


def _read_source_bytes(source: Any, options: ConversionOptions) -> tuple[bytes, str, str | None]:
    if isinstance(source, (bytes, bytearray, memoryview)):
        return bytes(source), "<bytes>", None

    if hasattr(source, "read") and callable(source.read):
        payload = source.read()
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        return bytes(payload), getattr(source, "name", "<file-like>"), None

    if isinstance(source, (str, os.PathLike)):
        raw = os.fspath(source)
        if isinstance(raw, str) and _is_url(raw):
            with urlopen(raw, timeout=options.url_timeout_seconds) as response:
                return response.read(), raw, None
        path = Path(raw)
        if path.exists():
            return path.read_bytes(), str(path), format_from_extension(path)
        if isinstance(raw, str) and any(char in raw for char in "*?[]"):
            raise ConversionError("convert() does not accept glob patterns; use convert_many().")
        raise ConversionError(f"Source does not exist: {raw}")

    raise ConversionError(f"Unsupported source type: {type(source).__name__}")


def _special_format(data: bytes, source_name: str | None, source_format: str | None) -> str | None:
    if source_format:
        return source_format.upper()
    suffix = Path(source_name or "").suffix.lower()
    head = data.lstrip()[:64].lower()
    if suffix == ".svg" or head.startswith(b"<svg") or b"svg" in head:
        return "SVG"
    if suffix == ".pdf" or data.startswith(b"%PDF"):
        return "PDF"
    if suffix in _RAW_EXTENSIONS:
        return "RAW"
    if suffix in {".heif", ".heic"}:
        return "HEIF"
    if suffix == ".avif":
        return "AVIF"
    return None


def _load_pillow_image(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    image.load()
    return image


def _decode_special_bytes(
    data: bytes,
    source_name: str | None,
    source_format: str | None,
    options: ConversionOptions,
) -> tuple[list[Image.Image], str | None]:
    special = _special_format(data, source_name, source_format)
    if special == "SVG":
        if importlib.util.find_spec("cairosvg") is None:
            raise UnsupportedFormatError("SVG conversion requires the optional `svg` extra (cairosvg).")
        import cairosvg

        return [_load_pillow_image(cairosvg.svg2png(bytestring=data))], "SVG"

    if special == "PDF":
        if importlib.util.find_spec("fitz") is None and importlib.util.find_spec("pymupdf") is None:
            raise UnsupportedFormatError("PDF conversion requires the optional `pdf` extra (PyMuPDF).")
        import fitz

        doc = fitz.open(stream=data, filetype="pdf")
        try:
            if options.frame == "all":
                page_indices = list(range(doc.page_count))
            elif isinstance(options.frame, int):
                page_indices = [options.frame]
            else:
                page_indices = [0]

            frames: list[Image.Image] = []
            for page_index in page_indices:
                if page_index < 0 or page_index >= doc.page_count:
                    raise ConversionError(f"PDF page index {page_index} is out of range.")
                page = doc.load_page(page_index)
                pix = page.get_pixmap(alpha=False)
                frames.append(_load_pillow_image(pix.tobytes("png")))
            return frames, "PDF"
        finally:
            doc.close()

    if special in {"HEIF", "AVIF"}:
        if importlib.util.find_spec("pillow_heif") is None:
            raise UnsupportedFormatError(
                f"{special} conversion requires the optional `heif` or `avif` extra (pillow-heif)."
            )
        import pillow_heif

        pillow_heif.register_heif_opener()

    if special == "RAW":
        if importlib.util.find_spec("rawpy") is None:
            raise UnsupportedFormatError("RAW conversion requires the optional `raw` extra (rawpy).")
        import rawpy

        suffix = Path(source_name or "image.raw").suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            with rawpy.imread(tmp_path) as raw:
                rgb = raw.postprocess()
            return [Image.fromarray(rgb)], "RAW"
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return [_load_pillow_image(data)], source_format.upper() if source_format else None


def _frame_images_from_pillow(image: Image.Image, frame: int | str | None) -> list[Image.Image]:
    if frame == "all":
        return [frame_image.copy() for frame_image in ImageSequence.Iterator(image)]
    if isinstance(frame, int):
        try:
            image.seek(frame)
        except EOFError as exc:
            raise ConversionError(f"Frame index {frame} is out of range.") from exc
        return [image.copy()]
    return [image.copy()]


def _transform_image(image: Image.Image, options: ConversionOptions, forced_mode: str | None = None) -> np.ndarray:
    working = image
    if options.resize is not None:
        resampling = getattr(Image, "Resampling", Image)
        working = working.resize(options.resize, resampling.LANCZOS)
    target_mode = options.channel_mode or forced_mode
    if target_mode is not None:
        working = working.convert(target_mode)
    array = np.array(working)
    if options.normalize_mode == "0..1":
        array = array.astype(np.float32) / 255.0
    elif options.normalize_mode == "-1..1":
        array = np.interp(array, (0, 255), (-1, 1)).astype(np.float32)
    elif options.normalize_mode != "none":
        raise ConversionError(f"Unsupported normalize mode: {options.normalize_mode}")
    if options.dtype:
        try:
            array = array.astype(options.dtype)
        except (TypeError, ValueError) as exc:
            raise ConversionError(f"Could not cast array to dtype: {options.dtype}") from exc
    if options.flatten:
        array = array.reshape(-1)
    return array


def _source_to_frames(source: Any, options: ConversionOptions) -> tuple[list[Image.Image], str, str | None, dict[str, Any]]:
    if isinstance(source, Image.Image):
        frames = _frame_images_from_pillow(source, options.frame)
        return frames, "<pil-image>", source.format, dict(source.info)

    data, source_name, source_format = _read_source_bytes(source, options)
    frames, detected_format = _decode_special_bytes(data, source_name, source_format, options)

    if len(frames) == 1 and detected_format not in {"PDF"}:
        frames = _frame_images_from_pillow(frames[0], options.frame)
    elif len(frames) > 1 and options.frame != "all":
        requested = options.frame if isinstance(options.frame, int) else 0
        if requested < 0 or requested >= len(frames):
            raise ConversionError(f"Frame index {requested} is out of range.")
        frames = [frames[requested]]

    metadata = dict(frames[0].info) if frames and options.preserve_metadata else {}
    return frames, source_name, detected_format, metadata


def _convert_frames(frames: list[Image.Image], options: ConversionOptions) -> np.ndarray:
    forced_mode = frames[0].mode if len(frames) > 1 and options.channel_mode is None else None
    arrays = [_transform_image(frame, options, forced_mode=forced_mode) for frame in frames]
    if len(arrays) == 1:
        return arrays[0]
    try:
        return np.stack(arrays)
    except ValueError as exc:
        raise ConversionError("Frames could not be stacked into a single array.") from exc


def convert_result(source: Any, options: ConversionOptions | None = None) -> ConversionResult:
    options = options or ConversionOptions()
    try:
        frames, source_name, detected_format, metadata = _source_to_frames(source, options)
        array = _convert_frames(frames, options)
        return ConversionResult(
            source=source_name,
            array=array,
            shape=tuple(array.shape),
            dtype=str(array.dtype),
            format=detected_format or (frames[0].format if frames else None),
            mode=frames[0].mode if frames else None,
            metadata=metadata if options.preserve_metadata else {},
        )
    except UnsupportedFormatError:
        raise
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Failed to convert source {source!r}: {exc}") from exc


def convert(source: Any, options: ConversionOptions | None = None) -> np.ndarray:
    result = convert_result(source, options=options)
    if result.array is None:
        raise ConversionError("Conversion unexpectedly returned no array.")
    return result.array


def _expand_source(source: Any) -> list[Any]:
    if isinstance(source, (bytes, bytearray, memoryview, Image.Image)):
        return [source]
    if hasattr(source, "read") and callable(source.read):
        return [source]
    if isinstance(source, (str, os.PathLike)):
        raw = os.fspath(source)
        if isinstance(raw, str) and _is_url(raw):
            return [raw]
        path = Path(raw)
        if path.is_dir():
            return [item for item in sorted(path.rglob("*")) if item.is_file()]
        if isinstance(raw, str) and any(char in raw for char in "*?[]"):
            return [Path(item) for item in sorted(glob.glob(raw, recursive=True)) if Path(item).is_file()]
        return [path]
    if isinstance(source, Iterable):
        expanded: list[Any] = []
        for item in source:
            expanded.extend(_expand_source(item))
        return expanded
    return [source]


def convert_many(source: Any, options: ConversionOptions | None = None, fail_fast: bool = False) -> BatchResult:
    options = options or ConversionOptions()
    results: list[ConversionResult] = []
    for item in _expand_source(source):
        try:
            results.append(convert_result(item, options=options))
        except Exception as exc:
            results.append(
                ConversionResult(
                    source=str(item),
                    array=None,
                    shape=None,
                    dtype=None,
                    error=str(exc),
                )
            )
            if fail_fast:
                break
    return BatchResult(results=results)
