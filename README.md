# img2numpy

img2numpy is being rebuilt as a Docker-first app with:

- A **browser UI** for quick upload/preview conversions.
- A **JSON API** for programmatic workflows.
- A small **legacy compatibility module** (`Img2Numpy.py`) preserved from the old project.

## What it does

Given an image file, img2numpy converts it to a NumPy array and returns:

- shape
- dtype
- full array (API)
- preview information (UI)

Supported image formats depend on Pillow and include common formats like PNG, JPEG, WEBP, and GIF.

## Quick start (Docker)

```bash
docker build -t img2numpy .
docker run --rm -p 8000:8000 img2numpy
```

Open `http://localhost:8000`.

## Quick start (local dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API usage

Endpoint:

- `POST /api/convert`

Multipart fields:

- `file` (required): image upload
- `color` (optional, default: `true`): keep color channels
- `normalize` (optional, default: `false`): normalize pixel values to `[-1, 1]`

Example:

```bash
curl -X POST "http://localhost:8000/api/convert" \
  -F "file=@/path/to/image.png" \
  -F "color=true" \
  -F "normalize=false"
```

## Tests

```bash
pip install -r requirements.txt
pip install pytest
pytest
```

## Legacy module

`Img2Numpy.py` still exposes:

- `img2numpy`
- `folder2numpy`
- `npz2array`
- `tuple2lists`
- `scrub_filename`

This helps older scripts continue to run while the new web/API app is built out.
