# img2numpy

`img2numpy` is a Docker-first service for turning image files into NumPy arrays for browser workflows and AI pipeline automation.

## Interfaces

- Browser UI: `GET /` and `POST /`
- Legacy API: `POST /api/convert` (JSON array payload)
- Versioned keyed API: `POST /api/v1/{api_key}/{command}`
- Artifact download API: `GET /api/v1/{api_key}/download/{artifact_id}`

## Quick Start

### Docker (manual)

```bash
docker build -t img2numpy:latest .
docker run --rm -p 8585:8585 -e IMG2NUMPY_API_PORT=8585 img2numpy:latest
```

- Browser UI: `http://127.0.0.1:8585`
- API: `http://127.0.0.1:8585`

### Scripted build/install/update

```bash
bash ./img2numpy.sh /build
bash ./img2numpy.sh /build -a
bash ./img2numpy.sh /install -p 8000
bash ./img2numpy.sh /update -p 8000
```

- `/build -a` builds multi-arch and pushes `172.16.120.5:5000/img2numpy:latest`.
- `-p` sets WebUI host port.
- API host port comes from `IMG2NUMPY_API_PORT` (default `8585`).

## Environment Variables

- `IMG2NUMPY_API_KEYS`: comma-separated API keys for `/api/v1/*` (default: `dev-local-key`)
- `IMG2NUMPY_API_PORT`: service port inside container/runtime (default: `8585`)
- `IMG2NUMPY_ARTIFACT_DIR`: directory for generated `.npz` artifacts (default: `./artifacts`)
- `IMG2NUMPY_ARTIFACT_TTL_SECONDS`: artifact lifetime in seconds (default: `3600`)
- `IMG2NUMPY_MAX_UPLOAD_BYTES`: max bytes per uploaded file (default: `52428800`)
- `IMG2NUMPY_MAX_BATCH_FILES`: max files per batch request (default: `250`)
- `IMG2NUMPY_MAX_PROCESS_SECONDS`: max processing time per batch request (default: `120`)
- `IMG2NUMPY_MAX_ARTIFACT_BYTES`: max total bytes allowed in artifact storage directory (default: `1073741824`)

## API v1 Reference

### Command Route Grammar

`POST /api/v1/{api_key}/{command}`

Reserved command names:

- `convert`: single-file conversion
- `batch`: multi-file conversion
- `download`: artifact download by `artifact_id` form field

Unknown commands return `404`.

### Convert Command

Endpoint:

- `POST /api/v1/{api_key}/convert`

Multipart fields:

- `file` (required)
- `output_mode` (`npz` default, `link` optional)
- `dtype` (optional cast, e.g. `float32`, `int16`)
- `normalize_mode` (`none`, `0..1`, `-1..1`)
- `channel_mode` (`RGB`, `RGBA`, `L`)
- `flatten` (`true`/`false`)
- `metadata_only` (`true`/`false`)

Default behavior: returns downloadable compressed `.npz`.

### Batch Command

Endpoint:

- `POST /api/v1/{api_key}/batch`

Multipart fields:

- `files` (repeat this field for multiple files)
- all convert fields above
- `fail_fast` (`false` default): when `false`, continue after per-file errors

Behavior:

- Mixed image formats in the same request are supported.
- Validation is decode-based (invalid/corrupt image payloads are reported per file).
- Returns compressed `.npz` by default.
- In `link` mode, returns JSON with `artifact_id`, `download_url`, and per-file status entries.

### Download Artifact

Endpoint:

- `GET /api/v1/{api_key}/download/{artifact_id}`

Returns the previously generated `.npz` artifact if not expired.

### Supported Format Matrix

Endpoint:

- `GET /api/v1/formats`

Current matrix includes PNG, JPEG, WEBP, GIF, BMP, and TIFF MIME/extension mappings.

## Output Contract

- Primary output is compressed NumPy archives (`.npz`).
- Optional link mode stores artifacts and returns an expiring download link payload.
- Batch artifacts include a `__manifest_json__` entry containing per-file result metadata.
- Errors are explicit (`400`, `401`, `404`, `408`, `413`) with actionable detail.

## Security

### API Key Setup

Set one or more keys:

```bash
export IMG2NUMPY_API_KEYS="key-one,key-two,key-three"
```

API keys are validated using constant-time comparison.

### Rotation Procedure

1. Add new key to `IMG2NUMPY_API_KEYS` alongside current keys.
2. Restart service and move clients to new key.
3. Remove old key and restart service again.

## Example Calls

### 1) Convert one image (default `.npz` response)

```bash
curl -X POST "http://127.0.0.1:8585/api/v1/dev-local-key/convert" \
  -F "file=@/path/to/image.png"
```

### 2) Convert one image and get artifact link JSON

```bash
curl -X POST "http://127.0.0.1:8585/api/v1/dev-local-key/convert" \
  -F "file=@/path/to/image.png" \
  -F "output_mode=link"
```

### 3) Batch convert mixed files (link mode with per-file results)

```bash
curl -X POST "http://127.0.0.1:8585/api/v1/dev-local-key/batch" \
  -F "files=@/data/frame1.png" \
  -F "files=@/data/frame2.jpg" \
  -F "files=@/data/frame3.webp" \
  -F "output_mode=link" \
  -F "fail_fast=false"
```

### 4) Download an artifact

```bash
curl -L "http://127.0.0.1:8585/api/v1/dev-local-key/download/<artifact_id>" -o result.npz
```

## Legacy Compatibility

`Img2Numpy.py` still exposes:

- `img2numpy`
- `folder2numpy`
- `npz2array`
- `tuple2lists`
- `scrub_filename`

## Tests

```bash
pip install -r requirements.txt
pytest -q
```
