import os
import time
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

os.environ["IMG2NUMPY_API_KEYS"] = "test-key"
os.environ["IMG2NUMPY_ARTIFACT_DIR"] = "tests/.artifacts"
os.environ["IMG2NUMPY_ARTIFACT_TTL_SECONDS"] = "600"
os.environ["IMG2NUMPY_API_KEY_STORE_PATH"] = "tests/.artifacts/api_keys.json"

KEY_STORE_PATH = Path(os.environ["IMG2NUMPY_API_KEY_STORE_PATH"])
if KEY_STORE_PATH.exists():
    KEY_STORE_PATH.unlink()

from app.main import api_key_store, app  # noqa: E402

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


def test_ui_single_conversion_with_full_options():
    files = [("files", ("ui.png", make_image("PNG"), "image/png"))]
    response = client.post(
        "/",
        data={
            "output_mode": "link",
            "dtype": "float32",
            "normalize_mode": "0..1",
            "channel_mode": "L",
            "flatten": "true",
        },
        files=files,
    )
    assert response.status_code == 200
    assert "Run Summary" in response.text
    assert "Download artifact (.npz)" in response.text
    assert "Per-file Results" in response.text


def test_ui_batch_fail_fast_control():
    files = [
        ("files", ("bad.bin", b"not-an-image", "application/octet-stream")),
        ("files", ("good.png", make_image("PNG"), "image/png")),
    ]
    response = client.post(
        "/",
        data={"output_mode": "link", "fail_fast": "true"},
        files=files,
    )
    assert response.status_code == 400
    assert "No files were converted successfully." in response.text


def test_webui_generate_key_and_use_for_api_client_profile():
    create_response = client.post(
        "/keys/generate",
        data={"client_name": "integration-suite-a", "description": "batch pipeline client"},
    )
    assert create_response.status_code == 200
    assert "Generated API key for client profile" in create_response.text

    key_record = next(record for record in api_key_store.list_records() if record.client_name == "integration-suite-a")
    files = {"file": ("tiny.png", make_image(), "image/png")}
    convert_response = client.post(f"/api/v1/{key_record.api_key}/convert", files=files)
    assert convert_response.status_code == 200
    assert "X-Artifact-Id" in convert_response.headers


def test_webui_revoke_key_blocks_further_api_usage():
    create_response = client.post("/keys/generate", data={"client_name": "integration-suite-b"})
    assert create_response.status_code == 200

    key_record = next(record for record in api_key_store.list_records() if record.client_name == "integration-suite-b")
    revoke_response = client.post("/keys/revoke", data={"key_id": key_record.key_id})
    assert revoke_response.status_code == 200
    assert "Revoked API key profile" in revoke_response.text

    files = {"file": ("tiny.png", make_image(), "image/png")}
    convert_response = client.post(f"/api/v1/{key_record.api_key}/convert", files=files)
    assert convert_response.status_code == 401


def _poll_job(status_url: str, timeout_seconds: float = 5.0):
    deadline = time.time() + timeout_seconds
    payload = None
    while time.time() < deadline:
        response = client.get(status_url)
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"done", "failed"}:
            return payload
        time.sleep(0.05)
    raise AssertionError(f"Job did not finish in {timeout_seconds}s; last payload={payload}")


def test_async_job_submission_status_manifest_and_stats():
    files = [
        ("files", ("frame1.png", make_image("PNG"), "image/png")),
        ("files", ("frame2.jpg", make_image("JPEG"), "image/jpeg")),
    ]
    metadata_json = (
        '{"global":{"split":"train","sensor":"camera-a"},'
        '"per_file":{"frame1.png":{"label":"cat"},"frame2.jpg":{"label":"dog"}}}'
    )
    submit = client.post(
        "/api/v1/test-key/jobs/submit",
        data={"metadata_json": metadata_json, "output_mode": "npz"},
        files=files,
    )
    assert submit.status_code == 200
    submit_payload = submit.json()
    assert submit_payload["job_id"]

    status_payload = _poll_job(submit_payload["status_url"])
    assert status_payload["status"] == "done"
    assert status_payload["artifact_id"]
    assert status_payload["artifact_sha256"]
    assert status_payload["download_url"]

    manifest_response = client.get(submit_payload["manifest_url"])
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["schema_version"] == "img2numpy.job_manifest.v1"
    assert manifest["converter_version"] == "0.1.0"
    assert manifest["ok_count"] == 2
    first = manifest["results"][0]
    assert "provenance" in first
    assert "source_sha256" in first["provenance"]
    assert "metadata" in first
    assert first["metadata"]["split"] == "train"

    stats_response = client.get(submit_payload["stats_url"])
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_sample_count"] == 2
    assert stats["valid_sample_count"] == 2
    assert stats["class_counts"]["cat"] == 1
    assert stats["class_counts"]["dog"] == 1


def test_async_job_optional_callback_is_recorded():
    files = [("files", ("frame1.png", make_image("PNG"), "image/png"))]
    submit = client.post(
        "/api/v1/test-key/jobs/submit",
        data={"callback_url": "http://127.0.0.1:1/callback"},
        files=files,
    )
    assert submit.status_code == 200
    status_payload = _poll_job(submit.json()["status_url"])
    assert status_payload["status"] in {"done", "failed"}
    assert status_payload["callback_url"] == "http://127.0.0.1:1/callback"
    if status_payload["callback_status"] is None:
        deadline = time.time() + 2
        while time.time() < deadline:
            status_payload = client.get(submit.json()["status_url"]).json()
            if status_payload["callback_status"] is not None:
                break
            time.sleep(0.05)
    assert status_payload["callback_status"] is not None
