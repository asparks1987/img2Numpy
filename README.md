# img2numpy

`img2numpy` is a Docker-first image-to-NumPy service with:

- Browser UI for single and batch conversions with full option control
- Versioned keyed API for synchronous conversions and artifact downloads
- Async job API for larger ingestion and AI-suite pipeline integration

Primary output format is compressed NumPy archives (`.npz`).

## Interfaces

- Browser UI: `GET /`, `POST /`
- Legacy API: `POST /api/convert`
- v1 command API: `POST /api/v1/{api_key}/{command}`
- Artifact download: `GET /api/v1/{api_key}/download/{artifact_id}`
- Async jobs:
  - `POST /api/v1/{api_key}/jobs/submit`
  - `GET /api/v1/{api_key}/jobs/{job_id}`
  - `GET /api/v1/{api_key}/jobs/{job_id}/manifest`
  - `GET /api/v1/{api_key}/jobs/{job_id}/stats`
- Supported-format matrix: `GET /api/v1/formats`

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

- `/build -a` performs multi-arch buildx push to `172.16.120.5:5000/img2numpy:latest`.
- `-p` controls the WebUI host port.
- API host port is controlled by `IMG2NUMPY_API_PORT` (default `8585`).

## Environment Variables

- `IMG2NUMPY_API_KEYS`: comma-separated API keys for `/api/v1/*` (default `dev-local-key`)
- `IMG2NUMPY_API_KEY_STORE_PATH`: persistent API key profile store file (default `<artifact_dir>/api_keys.json`)
- `IMG2NUMPY_API_PORT`: API/listen port (default `8585`)
- `IMG2NUMPY_ARTIFACT_DIR`: output artifact directory (default `./artifacts`)
- `IMG2NUMPY_ARTIFACT_TTL_SECONDS`: artifact expiration TTL in seconds (default `3600`)
- `IMG2NUMPY_MAX_UPLOAD_BYTES`: max bytes per uploaded file (default `52428800`)
- `IMG2NUMPY_MAX_BATCH_FILES`: max files per batch call (default `250`)
- `IMG2NUMPY_MAX_PROCESS_SECONDS`: max processing time per batch/job (default `120`)
- `IMG2NUMPY_MAX_ARTIFACT_BYTES`: max total artifact store bytes (default `1073741824`)

## Browser UI

`POST /` supports:

- multi-file uploads (`files`, repeated)
- `output_mode` (`npz` default, `link` optional)
- `dtype`
- `normalize_mode` (`none`, `0..1`, `-1..1`)
- `channel_mode` (`RGB`, `RGBA`, `L`, or auto)
- `flatten`
- `metadata_only`
- `fail_fast` (applies in batch mode)

UI result cards include run summary, applied settings, per-file statuses, preview for first successful file, and artifact download link when generated.

### WebUI API key profiles

The browser UI includes an **API Key Profiles** section to:

- generate one key per client app/profile
- persist keys on disk (`IMG2NUMPY_API_KEY_STORE_PATH`)
- revoke keys when a client should lose access
- inspect created/last-used timestamps per key

Use generated keys as `{api_key}` in v1 command routes.

## v1 Command API

### Route grammar

`POST /api/v1/{api_key}/{command}`

Reserved commands:

- `convert`
- `batch`
- `download`

Unknown command returns `404`.

### Common multipart fields

- `output_mode`: `npz` (default) or `link`
- `dtype`
- `normalize_mode`: `none`, `0..1`, `-1..1`
- `channel_mode`: `RGB`, `RGBA`, `L`
- `flatten`: boolean
- `metadata_only`: boolean

### `convert`

- Required field: `file`
- Default response: downloadable `.npz`
- `output_mode=link`: returns JSON with `artifact_id` + `download_url`

### `batch`

- Required field: one or more `files`
- Additional field: `fail_fast` (`false` default)
- Mixed formats allowed in one request (decode-based validation)
- Per-file status metadata returned in link mode

### `download`

- Field: `artifact_id` (multipart form)
- Returns artifact stream

### Artifact download endpoint

- `GET /api/v1/{api_key}/download/{artifact_id}`

## Async Job API

### Submit

`POST /api/v1/{api_key}/jobs/submit`

Multipart fields:

- `files` (repeat for batch input)
- all conversion fields from command API
- `metadata_json` (optional JSON object)
  - supported shape:
    - `global`: metadata merged into all samples
    - `per_file`: filename-keyed metadata overrides
- `callback_url` (optional): completion callback target

Response:

- `job_id`
- `status` (`queued`)
- `status_url`
- `manifest_url`
- `stats_url`

### Job status

`GET /api/v1/{api_key}/jobs/{job_id}`

Returns:

- lifecycle fields: `queued`, `running`, `done`, `failed`
- artifact metadata (`artifact_id`, `artifact_sha256`, download URL)
- callback state (`callback_url`, `callback_status`)
- links to manifest/stats endpoints

### Manifest

`GET /api/v1/{api_key}/jobs/{job_id}/manifest`

Includes:

- `schema_version` and `converter_version`
- per-sample `sample_id`, `artifact_key`, status, shape/dtype
- provenance (`source_filename`, `source_sha256`, `ingest_timestamp`, `job_id`)
- metadata passthrough values
- aggregate counts (`ok_count`, `error_count`)

### Stats

`GET /api/v1/{api_key}/jobs/{job_id}/stats`

Includes:

- `shape_distribution`
- `class_counts`
- `split_counts`
- `missing_labels`
- valid/invalid/total sample counts

## Supported Input Matrix

`GET /api/v1/formats`

Current matrix covers:

- PNG
- JPEG
- WEBP
- GIF
- BMP
- TIFF

## Output + Integrity Model

- `.npz` is the primary/default response format
- link mode returns artifact references for deferred retrieval
- batch and job artifacts embed a `__manifest_json__` entry
- async jobs compute and report artifact `sha256`
- artifact retention is TTL-based with background cleanup

## Security

### API keys

```bash
export IMG2NUMPY_API_KEYS="key-one,key-two,key-three"
```

Validation uses constant-time comparison.

Runtime behavior:

- API keys loaded from `IMG2NUMPY_API_KEY_STORE_PATH` are authoritative.
- On first start, keys from `IMG2NUMPY_API_KEYS` seed the persistent store.
- Key usage updates `last_used_at` timestamps for profile tracking.

### Rotation

1. Add new key to `IMG2NUMPY_API_KEYS` alongside existing keys.
2. Restart service and migrate clients.
3. Remove old key and restart again.

## Example Calls

### Convert one file (default `.npz`)

```bash
curl -X POST "http://127.0.0.1:8585/api/v1/dev-local-key/convert" \
  -F "file=@/data/frame.png"
```

### Batch convert mixed files (link mode, continue on error)

```bash
curl -X POST "http://127.0.0.1:8585/api/v1/dev-local-key/batch" \
  -F "files=@/data/a.png" \
  -F "files=@/data/b.jpg" \
  -F "files=@/data/c.webp" \
  -F "output_mode=link" \
  -F "fail_fast=false"
```

### Submit async job with metadata passthrough

```bash
curl -X POST "http://127.0.0.1:8585/api/v1/dev-local-key/jobs/submit" \
  -F "files=@/data/a.png" \
  -F "files=@/data/b.jpg" \
  -F 'metadata_json={"global":{"split":"train"},"per_file":{"a.png":{"label":"cat"},"b.jpg":{"label":"dog"}}}'
```

### Poll status and fetch manifest

```bash
curl "http://127.0.0.1:8585/api/v1/dev-local-key/jobs/<job_id>"
curl "http://127.0.0.1:8585/api/v1/dev-local-key/jobs/<job_id>/manifest"
curl "http://127.0.0.1:8585/api/v1/dev-local-key/jobs/<job_id>/stats"
```

### Download artifact

```bash
curl -L "http://127.0.0.1:8585/api/v1/dev-local-key/download/<artifact_id>" -o output.npz
```

## Legacy compatibility

`Img2Numpy.py` still provides:

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
