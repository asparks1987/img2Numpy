from __future__ import annotations

import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from img2numpy import (
    BatchResult,
    ConversionOptions,
    ConversionResult,
    ConversionError,
    NPZLoadResult,
    UnsupportedFormatError,
    convert,
    convert_many,
    convert_result,
    decoder_capabilities,
    load_npz,
    save_npz,
    supported_formats,
)


def make_image_bytes(fmt: str = "PNG", mode: str = "RGB", color=(255, 0, 0)) -> bytes:
    image = Image.new(mode, (3, 2), color=color if mode == "RGB" else 128)
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def make_animated_gif_bytes() -> bytes:
    first = Image.new("RGB", (2, 2), color=(255, 0, 0))
    second = Image.new("RGB", (2, 2), color=(0, 0, 255))
    buffer = BytesIO()
    first.save(buffer, format="GIF", save_all=True, append_images=[second], loop=0, duration=10)
    return buffer.getvalue()


@contextmanager
def serve_bytes(payload: bytes, content_type: str = "image/png"):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format, *args):  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/image"
    finally:
        server.shutdown()
        thread.join(timeout=1)
        server.server_close()


def test_convert_supports_common_input_types(tmp_path: Path):
    payload = make_image_bytes()
    path = tmp_path / "sample.png"
    path.write_bytes(payload)

    path_array = convert(path)
    bytes_array = convert(payload)
    file_array = convert(BytesIO(payload))
    pil_array = convert(Image.open(BytesIO(payload)))
    detailed = convert_result(path)

    with serve_bytes(payload) as url:
        url_array = convert(url)

    assert isinstance(detailed, ConversionResult)
    assert detailed.shape == (2, 3, 3)
    assert path_array.shape == detailed.shape
    assert bytes_array.shape == detailed.shape
    assert file_array.shape == detailed.shape
    assert pil_array.shape == detailed.shape
    assert url_array.shape == detailed.shape
    assert np.array_equal(path_array, bytes_array)


def test_convert_many_expands_directories_and_mixed_iterables(tmp_path: Path):
    png = tmp_path / "one.png"
    jpg = tmp_path / "two.jpg"
    bad = tmp_path / "note.txt"
    png.write_bytes(make_image_bytes("PNG"))
    jpg.write_bytes(make_image_bytes("JPEG"))
    bad.write_text("not an image", encoding="utf-8")

    directory_batch = convert_many(tmp_path)
    assert isinstance(directory_batch, BatchResult)
    assert directory_batch.total_count == 3
    assert directory_batch.ok_count == 2
    assert directory_batch.error_count == 1

    glob_batch = convert_many(str(tmp_path / "*.png"))
    assert glob_batch.total_count == 1
    assert glob_batch.ok_count == 1

    mixed_batch = convert_many([png, BytesIO(make_image_bytes()), make_image_bytes("PNG")])
    assert mixed_batch.total_count == 3
    assert mixed_batch.ok_count == 3


def test_convert_many_fail_fast_and_frame_resize_options():
    payload = make_animated_gif_bytes()
    options = ConversionOptions(frame="all", resize=(1, 1), normalize_mode="0..1", channel_mode="RGB")

    result = convert_result(payload, options=options)
    assert result.shape == (2, 1, 1, 3)
    assert result.array.min() >= 0
    assert result.array.max() <= 1

    batch = convert_many([b"not-an-image", make_image_bytes()], fail_fast=True)
    assert batch.total_count == 1
    assert batch.error_count == 1


def test_npz_round_trip_and_manifest(tmp_path: Path):
    arrays = {"sample_a": np.arange(6).reshape(2, 3)}
    manifest = {"source": "sdk-test", "count": 1}
    path = save_npz(arrays, tmp_path / "bundle", manifest=manifest)

    loaded = load_npz(path)
    assert isinstance(loaded, NPZLoadResult)
    assert loaded.manifest == manifest
    assert np.array_equal(loaded.arrays["sample_a"], arrays["sample_a"])


def test_supported_formats_and_capabilities_structure():
    formats = supported_formats()
    capabilities = decoder_capabilities()

    assert any(item["format"] == "PNG" for item in formats)
    assert "pillow" in capabilities
    assert "svg" in capabilities


def test_unsupported_format_error_is_actionable(monkeypatch):
    import img2numpy.core as core

    original_find_spec = core.importlib.util.find_spec

    def fake_find_spec(name):
        if name == "cairosvg":
            return None
        return original_find_spec(name)

    monkeypatch.setattr(core.importlib.util, "find_spec", fake_find_spec)

    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2"><rect width="2" height="2" fill="red"/></svg>'
    try:
        convert_result(svg, options=ConversionOptions())
    except UnsupportedFormatError as exc:
        assert "svg" in str(exc).lower()
    else:
        raise AssertionError("Expected UnsupportedFormatError")


def test_convert_is_the_simple_array_returning_entry_point():
    array = convert(make_image_bytes())
    assert isinstance(array, np.ndarray)
    assert array.shape == (2, 3, 3)
