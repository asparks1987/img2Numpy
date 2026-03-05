import os
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

os.environ["IMG2NUMPY_API_KEYS"] = "test-key"
os.environ["IMG2NUMPY_ARTIFACT_DIR"] = "tests/.artifacts"
os.environ["IMG2NUMPY_ARTIFACT_TTL_SECONDS"] = "600"

from app.main import app  # noqa: E402

client = TestClient(app)


def make_image(fmt: str = "PNG", mode: str = "RGB") -> bytes:
    image = Image.new(mode, (3, 2), color=(20, 40, 60) if mode == "RGB" else 20)
    buf = BytesIO()
    image.save(buf, format=fmt)
    return buf.getvalue()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_convert_legacy_route():
    files = {"file": ("tiny.png", make_image(), "image/png")}
    response = client.post("/api/convert", files=files)
    payload = response.json()

    assert response.status_code == 200
    assert payload["filename"] == "tiny.png"
    assert payload["shape"] == [2, 3, 3]


def test_v1_rejects_invalid_api_key():
    files = {"file": ("tiny.png", make_image(), "image/png")}
    response = client.post("/api/v1/bad-key/convert", files=files)
    assert response.status_code == 401


def test_v1_unknown_command():
    files = {"file": ("tiny.png", make_image(), "image/png")}
    response = client.post("/api/v1/test-key/unknown", files=files)
    assert response.status_code == 404


def test_v1_convert_returns_npz_by_default():
    files = {"file": ("tiny.png", make_image(), "image/png")}
    response = client.post("/api/v1/test-key/convert", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert "X-Artifact-Id" in response.headers
    assert len(response.content) > 0


def test_v1_convert_link_mode_and_download_endpoint():
    files = {"file": ("tiny.png", make_image(), "image/png")}
    response = client.post(
        "/api/v1/test-key/convert",
        data={"output_mode": "link"},
        files=files,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact"]["artifact_id"]
    assert payload["artifact"]["download_url"]

    download_response = client.get(payload["artifact"]["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/octet-stream"


def test_v1_download_command_via_router():
    files = {"file": ("tiny.png", make_image(), "image/png")}
    response = client.post(
        "/api/v1/test-key/convert",
        data={"output_mode": "link"},
        files=files,
    )
    artifact_id = response.json()["artifact"]["artifact_id"]

    download_response = client.post(
        "/api/v1/test-key/download",
        data={"artifact_id": artifact_id},
    )
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/octet-stream"


def test_v1_batch_mixed_files_continue_on_error():
    files = [
        ("files", ("one.png", make_image("PNG"), "image/png")),
        ("files", ("two.jpg", make_image("JPEG"), "image/jpeg")),
        ("files", ("bad.bin", b"not-an-image", "application/octet-stream")),
    ]
    response = client.post(
        "/api/v1/test-key/batch",
        data={"output_mode": "link", "fail_fast": "false"},
        files=files,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact"]["artifact_id"]
    assert any(item["status"] == "ok" for item in payload["results"])
    assert any(item["status"] == "error" for item in payload["results"])


def test_v1_batch_mixed_valid_files_returns_npz():
    files = [
        ("files", ("one.png", make_image("PNG"), "image/png")),
        ("files", ("two.jpg", make_image("JPEG"), "image/jpeg")),
        ("files", ("three.webp", make_image("WEBP"), "image/webp")),
    ]
    response = client.post("/api/v1/test-key/batch", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert "X-Artifact-Id" in response.headers


def test_v1_batch_fail_fast_stops_on_error():
    files = [
        ("files", ("bad.bin", b"not-an-image", "application/octet-stream")),
        ("files", ("one.png", make_image("PNG"), "image/png")),
    ]
    response = client.post(
        "/api/v1/test-key/batch",
        data={"output_mode": "link", "fail_fast": "true"},
        files=files,
    )
    assert response.status_code == 400
    assert "No files were converted successfully." in str(response.json()["detail"])


def test_v1_invalid_output_mode_returns_400():
    files = {"file": ("tiny.png", make_image(), "image/png")}
    response = client.post(
        "/api/v1/test-key/convert",
        data={"output_mode": "invalid"},
        files=files,
    )
    assert response.status_code == 400


def test_v1_convert_requires_file():
    response = client.post("/api/v1/test-key/convert", data={"output_mode": "link"})
    assert response.status_code == 400


def test_supported_formats_endpoint():
    response = client.get("/api/v1/formats")
    assert response.status_code == 200
    payload = response.json()
    assert "supported" in payload
    assert any(item["format"] == "PNG" for item in payload["supported"])
