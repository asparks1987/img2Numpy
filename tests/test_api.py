from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def make_image() -> bytes:
    image = Image.new("RGB", (3, 2), color=(20, 40, 60))
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_convert():
    files = {"file": ("tiny.png", make_image(), "image/png")}
    response = client.post("/api/convert", files=files)
    payload = response.json()

    assert response.status_code == 200
    assert payload["filename"] == "tiny.png"
    assert payload["shape"] == [2, 3, 3]
