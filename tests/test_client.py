from __future__ import annotations

from io import BytesIO

import httpx
from PIL import Image

from img2numpy.client import Img2NumpyClient


def make_image_bytes() -> bytes:
    image = Image.new("RGB", (2, 2), color=(20, 40, 60))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_client_composes_requests_and_handles_responses(monkeypatch, tmp_path):
    captured = []

    def fake_request(method, url, files=None, data=None, timeout=None):
        captured.append({"method": method, "url": url, "files": files, "data": data, "timeout": timeout})
        request = httpx.Request(method, url)
        if url.endswith("/convert"):
            return httpx.Response(200, json={"artifact": {"artifact_id": "art-1"}}, request=request)
        if url.endswith("/jobs/submit"):
            return httpx.Response(200, json={"job_id": "job-1"}, request=request)
        if url.endswith("/download/art-1"):
            return httpx.Response(200, content=b"npz-bytes", request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    monkeypatch.setattr("img2numpy.client.httpx.request", fake_request)

    image_path = tmp_path / "sample.png"
    image_path.write_bytes(make_image_bytes())

    client = Img2NumpyClient(base_url="http://example.test", api_key="key-1", timeout=9.5)
    convert_payload = client.convert(image_path)
    submit_payload = client.submit_job([image_path], metadata={"split": "train"})
    download_payload = client.download_artifact("art-1", path=tmp_path / "artifact.npz")

    assert convert_payload["artifact"]["artifact_id"] == "art-1"
    assert submit_payload["job_id"] == "job-1"
    assert download_payload == tmp_path / "artifact.npz"
    assert download_payload.read_bytes() == b"npz-bytes"
    assert any(entry["method"] == "POST" and entry["url"].endswith("/convert") for entry in captured)
    assert any(entry["method"] == "POST" and entry["url"].endswith("/jobs/submit") for entry in captured)
    assert any(entry["method"] == "GET" and entry["url"].endswith("/download/art-1") for entry in captured)

