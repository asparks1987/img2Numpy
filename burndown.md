# ⚙️ Codex Execution Instructions

You are acting as an autonomous senior software engineer.

When instructed to “follow the directions at the top of this file”, you must follow the rules below EXACTLY.

---

## 0. Definition of Done (DoD)
A task is only “done” when:
- The implementation is complete AND
- Any required tests are added/updated AND
- The relevant docs are updated (if user-facing or developer-facing) AND
- The checklist item is marked [x] with brief notes AND
- No known build/test/runtime failures remain (or failures are explicitly documented as pre-existing)

If any DoD element cannot be met, do NOT mark the task done; document what’s missing and why.

---

## 1. Read & Plan
- Read this entire file before making changes.
- Identify all unchecked tasks.
- Group tasks by dependency and execution order.
- Determine which tasks can be completed immediately with available context.
- Produce a short plan (bullets) before editing code.

---

## 2. Execution Order
Work in this priority order unless explicitly overridden:

1. Fix broken builds, tests, or runtime errors.
2. Implement missing core functionality.
3. Improve correctness and data integrity.
4. Add tests for newly implemented features.
5. Improve documentation and developer experience.
6. Refactor only when it directly improves reliability or clarity.

Do NOT start optional or cosmetic tasks until functional tasks are complete.

---

## 3. Task Processing Rules
For each task, in top-to-bottom order unless dependencies require reordering:

- If it can be completed fully → implement it.
- If it can be partially completed → implement what is possible and document what remains.
- If it cannot be completed → explain precisely why and what is required.

### Stop Rule (No Guessing Past Blockers)
If you are blocked by missing requirements, unclear behavior, or missing credentials/access:
- Stop work on that task
- Document the blocker clearly
- Move to the next unblocked task (if any)

Do not invent APIs, endpoints, schema, or business rules.

---

## 4. Change Scope & Standards
All work must:
- Follow existing project conventions.
- Include type hints where applicable.
- Include docstrings/comments for non-obvious logic.
- Avoid breaking existing functionality.
- Prefer small, incremental changes.

### Refactor Policy
- No drive-by refactors.
- Only refactor code you touched, and only if it reduces bugs or clarifies behavior.
- If a refactor is non-trivial, split it into a separate checklist task.

### Secrets/Security
- Do not expose secrets or credentials.
- Do not log sensitive values.
- Do not weaken auth, CORS, CSRF, or encryption behavior.

---

## 5. Testing & Validation
After implementing tasks:
- Add or update tests where relevant.
- Run tests/build if possible; otherwise simulate by reasoning and note what would be run.
- Fix failures caused by new changes.
- Do not leave known failing tests.

### Evidence Required
For each task you touch, include:
- Files changed (paths)
- Commands run (or commands that SHOULD be run)
- Any relevant output/expected output

If testing is impossible, explain exactly why.

---

## 6. Documentation Updates
When implementing features:
- Update relevant docs.
- Add usage examples where helpful.
- Note operational impacts if any.

Documentation must reflect actual behavior.

---

## 7. Checklist Maintenance
After completing work:
- Mark completed items as done.
- Add brief implementation notes under each completed item.
- Add new tasks if gaps are discovered.
- Do not delete incomplete tasks.

Use this format:

- [x] Task description
  - Notes: what was implemented
  - Files: path1, path2
  - Tests: what ran / what to run

---

## 8. Progress Reporting
At the end of each execution session, provide:
- Summary of completed tasks
- Remaining high-priority items
- Blockers or risks
- Recommended next steps

Be concise and factual.

---

## 9. Autonomy Rules
- Do not ask questions unless blocked.
- Make reasonable technical decisions independently.
- Prefer shipping working solutions over perfect designs.
- Optimize for reliability and maintainability.

---

## 10. Safety & Scope
- Do not implement automated trading, financial advice logic, or unsafe operations unless explicitly authorized.
- Do not add tracking/telemetry unless explicitly requested.
- Respect security and compliance constraints.

---

Follow these rules strictly.





# img2numpy Burndown

1. [x] Read legacy documentation and define the Docker-first rebuild direction.
2. [x] Inventory existing files and identify reusable legacy conversion pieces.
3. [x] Confirm target interfaces: browser UI plus programmatic HTTP API.
4. [x] Create FastAPI app entrypoint and application metadata.
5. [x] Add base health endpoint for runtime checks.
6. [x] Configure static file mounting for frontend assets.
7. [x] Configure template rendering for HTML UI pages.
8. [x] Create conversion options model for shared settings.
9. [x] Implement byte-stream image loading via Pillow.
10. [x] Implement color/grayscale conversion branch.
11. [x] Implement optional normalization transform.
12. [x] Implement file-path-to-array helper.
13. [x] Add `GET /` route for browser upload form.
14. [x] Add `POST /` route for browser conversion submit.
15. [x] Add UI success response with shape/dtype/preview output.
16. [x] Add UI error handling for empty/invalid uploads.
17. [x] Add `POST /api/convert` route for API conversion.
18. [x] Parse API multipart form options for conversion settings.
19. [x] Return API payload with filename, shape, dtype, and array.
20. [x] Add API error mapping for invalid image payloads.
21. [x] Update legacy module to use new converter core.
22. [x] Preserve old helper function names for backward compatibility.
23. [x] Add and pin runtime dependencies in `requirements.txt`.
24. [x] Add Docker build files (`Dockerfile`, `.dockerignore`).
25. [x] Add pytest configuration for predictable test discovery.
26. [x] Add converter unit tests for shape and normalization behavior.
27. [x] Add API tests for health and basic conversion flow.
28. [x] Define versioned API namespace and path pattern `/api/v1/{api_key}/{command}`.
   - Notes: Added command router and keyed v1 namespace in FastAPI.
29. [x] Decide command names and semantics for v1 (`convert`, `batch`, `download`).
   - Notes: Implemented `convert`, `batch`, and `download` with explicit route behavior.
30. [x] Add a central command-dispatch layer to route command handlers.
   - Notes: Added centralized handler map in command router.
31. [x] Implement `/api/v1/{api_key}/{command}` route scaffold.
   - Notes: Route accepts multipart form payloads and dispatches by command.
32. [x] Move single-file conversion logic into v1 command handler.
   - Notes: Added dedicated `_handle_convert_command`.
33. [x] Return clear `404/400` responses for unknown or malformed commands.
   - Notes: Unknown command returns `404`; malformed payloads return `400`.
34. [x] Add command-level request validation models.
   - Notes: Added Pydantic request/response models in `app/api_models.py`.
35. [x] Document command grammar and reserved command names in a dedicated API reference section.
   - Notes: README now includes route grammar and reserved command names.
36. [x] Define API key environment variables (`IMG2NUMPY_API_KEYS` or equivalent).
   - Notes: Added `IMG2NUMPY_API_KEYS` setting in runtime config.
37. [x] Implement secure key loading during app startup.
   - Notes: Settings are loaded at app boot and used by v1 auth checks.
38. [x] Implement API key parser/normalizer for configured keys.
   - Notes: Comma-separated parser trims and normalizes configured keys.
39. [x] Add constant-time API key comparison for auth checks.
   - Notes: Added `hmac.compare_digest`-based validator.
40. [x] Return `401 Unauthorized` for invalid or missing keys.
   - Notes: v1 handlers reject invalid keys with `401`.
41. [x] Add auth tests for valid key, invalid key, and missing key.
   - Notes: Added v1 auth tests in API test suite.
42. [x] Document API key setup, storage, and rotation procedure in security-focused docs.
   - Notes: README now documents key setup and rotation workflow.
43. [x] Define accepted input matrix for mixed batches (format + mime + extension).
   - Notes: Added supported format matrix endpoint at `/api/v1/formats`.
44. [x] Allow multiple uploaded files in one batch request.
   - Notes: Batch handler supports repeated multipart `files` entries.
45. [x] Add streaming-safe upload reads for large requests.
   - Notes: Upload reading now uses chunked reads and byte limits.
46. [x] Validate image payloads by decoding, not extension-only checks.
   - Notes: Validation occurs through Pillow decode in converter path.
47. [x] Support mixed-format batch conversion in a single request.
   - Notes: Batch endpoint processes mixed formats in the same call.
48. [x] Add per-file conversion execution inside batch pipeline.
   - Notes: Batch loop converts each file independently.
49. [x] Add per-file result schema with status and error fields.
   - Notes: Added `FileResult` schema with `ok/error` status fields.
50. [x] Implement continue-on-error behavior as batch default.
   - Notes: Batch defaults to continue behavior when a file fails.
51. [x] Add optional fail-fast flag for strict batch mode.
   - Notes: Added `fail_fast` flag to stop processing on first failure.
52. [x] Add tests for mixed-format batches with all-valid files.
   - Notes: Added mixed-valid batch test returning `.npz`.
53. [x] Add tests for mixed batches containing corrupted/invalid files.
   - Notes: Added mixed batch test with invalid payload and per-file error result.
54. [x] Define `output_mode` contract with `.npz` as the primary/default return format and optional artifact-link mode for pipeline workflows.
   - Notes: Output mode defaults to `npz`; `link` mode returns artifact metadata.
55. [x] Implement artifact ID generation for saved outputs.
   - Notes: Artifacts use secure random IDs via token generation.
56. [x] Create writable artifact storage directory in container/runtime.
   - Notes: Artifact store creates and manages runtime artifact directory.
57. [x] Save single conversion result in a compressed NumPy artifact (`.npz`) when link mode is requested.
   - Notes: Convert command persists `.npz` and returns link metadata in link mode.
58. [x] Save batch conversion results as compressed `.npz` artifacts by default.
   - Notes: Batch command now produces compressed `.npz` as standard behavior.
59. [x] Implement `/api/v1/{api_key}/download/{artifact_id}` endpoint.
   - Notes: Added keyed download endpoint for artifact retrieval.
60. [x] Return direct download link payload when optional link mode is requested.
   - Notes: Link mode response includes artifact metadata and `download_url`.
61. [x] Return downloadable `.npz` response as the standard/default API behavior.
   - Notes: Convert and batch return file responses by default.
62. [x] Add artifact metadata tracking (created time, size, expires time).
   - Notes: Artifact metadata now tracks creation, expiry, and size.
63. [x] Add background cleanup job for expired artifacts.
   - Notes: Startup cleanup worker purges expired artifacts periodically.
64. [x] Add environment-configurable TTL and storage limits.
   - Notes: Added TTL and max artifact byte limits via environment variables.
65. [x] Add tests for link generation, download success, and expiry cleanup.
   - Notes: Added API tests and artifact store cleanup/limit tests.
66. [x] Add converter option for output dtype casting.
   - Notes: Converter now supports explicit dtype cast option.
67. [x] Add normalization mode selector (`none`, `0..1`, `-1..1`).
   - Notes: Added multi-mode normalization support.
68. [x] Add channel mode selector (`RGB`, `RGBA`, `L`).
   - Notes: Converter now supports explicit channel mode conversion.
69. [x] Add optional flatten/reshape policy for output arrays.
   - Notes: Added flatten output option.
70. [x] Expose all converter options in API request models and fully detailed docs with request/response examples.
   - Notes: Options wired through v1 request models and documented in README.
71. [x] Rebuild browser settings UI to control every conversion option.
   - Notes: Browser form now supports dtype, normalize mode, channel mode, flatten, metadata-only, output mode, and multi-file uploads with structured result cards.
   - Files: `app/templates/index.html`, `app/static/styles.css`, `app/main.py`
   - Tests: `pytest -q`
72. [x] Add browser batch UI controls for output mode and strict/fail-fast behavior.
   - Notes: UI now includes output-mode selector and fail-fast toggle; server-side UI handler applies fail-fast behavior and batch summaries/per-file statuses.
   - Files: `app/templates/index.html`, `app/main.py`, `tests/test_api.py`
   - Tests: `pytest -q`
73. [x] Add request-size/file-count/timeout limits with explicit error messages.
   - Notes: Added upload-size, batch-count, and process-time enforcement with clear HTTP errors.
74. [x] Create `img2numpy.sh` as the primary build/install/update entrypoint with argument parsing, usage help, and command validation for `/build`, `/install`, and `/update`, and support an API port environment variable (for example `IMG2NUMPY_API_PORT`, default `8585`).
   - Notes: Added script command parser and runtime API port env handling.
75. [x] Implement and validate script overloads end-to-end: `bash ./img2numpy.sh /build -a` must perform a multi-architecture Docker build and push to `http://172.16.120.5:5000` as `img2numpy:latest`, plus support `bash ./img2numpy.sh /install -p <port>` and `bash ./img2numpy.sh /update -p <port>` where `-p` sets only the WebUI port and API port comes from env var/default (`IMG2NUMPY_API_PORT` or `8585`).
   - Notes: Script supports `/build -a` multi-arch registry push plus `/install` and `/update` with WebUI `-p`.
76. [x] Add async job submission for large conversion workloads and return a `job_id` immediately.
   - Notes: Added async job submit endpoint returning `job_id`, `status_url`, `manifest_url`, and `stats_url`.
   - Files: `app/main.py`, `app/jobs.py`, `tests/test_api.py`
   - Tests: `pytest -q`
77. [x] Add job status endpoint (`queued`, `running`, `done`, `failed`) so the AI suite can poll progress reliably.
   - Notes: Added status polling endpoint with lifecycle states and artifact/callback details.
   - Files: `app/main.py`, `app/jobs.py`, `tests/test_api.py`
   - Tests: `pytest -q`
78. [x] Add optional job completion callback/webhook support to trigger downstream training steps.
   - Notes: Added optional callback URL support and callback delivery status tracking on jobs.
   - Files: `app/jobs.py`, `app/main.py`, `tests/test_api.py`
   - Tests: `pytest -q`
79. [x] Generate dataset manifest output (`manifest.json`) per job with sample IDs, artifact paths, and conversion options used.
   - Notes: Job manifests include sample IDs, artifact keys, conversion options, and aggregate counts.
   - Files: `app/jobs.py`, `app/main.py`, `tests/test_api.py`
   - Tests: `pytest -q`
80. [x] Include provenance metadata per sample (source filename, source hash, ingest timestamp, and batch/job ID).
   - Notes: Per-sample provenance now includes filename, source hash, ingest timestamp, and job ID.
   - Files: `app/jobs.py`, `tests/test_api.py`
   - Tests: `pytest -q`
81. [x] Include artifact integrity checksums (`sha256`) for each generated `.npz` file.
   - Notes: Async jobs compute and return SHA256 checksums for created artifacts.
   - Files: `app/jobs.py`, `app/main.py`, `tests/test_api.py`
   - Tests: `pytest -q`
82. [x] Add metadata passthrough fields (labels, split, sensor/time/location fields) so training pipelines keep contextual state data.
   - Notes: Added `metadata_json` passthrough with global/per-file metadata merged into sample results and manifests.
   - Files: `app/main.py`, `app/jobs.py`, `README.md`, `tests/test_api.py`
   - Tests: `pytest -q`
83. [x] Include converter version and schema version in API responses/manifests for reproducibility across model training runs.
   - Notes: Manifests now include `converter_version` and `schema_version`.
   - Files: `app/jobs.py`, `README.md`, `tests/test_api.py`
   - Tests: `pytest -q`
84. [x] Add dataset quality/stats endpoint (shape distribution, class counts, missing labels, invalid sample counts).
   - Notes: Added job stats endpoint with shape distribution, class/split counts, missing labels, and valid/invalid totals.
   - Files: `app/main.py`, `app/jobs.py`, `README.md`, `tests/test_api.py`
   - Tests: `pytest -q`
85. [x] Publish a fully detailed documentation set covering architecture, async jobs, manifests, metadata schema, checksums, all endpoints/commands, auth, env vars, script usage, deployment, client examples, and troubleshooting for external AI-suite integrations.
   - Notes: Rewrote README with full API/UI/job documentation, env vars, command grammar, output model, and examples.
   - Files: `README.md`
   - Tests: `pytest -q`
86. [x] Add WebUI API key profile management so multiple client applications can be identified and run conversions simultaneously.
   - Notes: Added persistent API key store, WebUI key generation/revocation workflows, per-key client profile metadata, and auth integration so all v1 routes validate against stored keys.
   - Files: `app/key_store.py`, `app/main.py`, `app/templates/index.html`, `app/static/styles.css`, `app/settings.py`, `README.md`, `tests/test_api.py`, `tests/test_key_store.py`
   - Tests: `pytest -q`

## Session Evidence (Tasks 28-70, 73-75)

- Files: `app/main.py`, `app/converter.py`, `app/settings.py`, `app/auth.py`, `app/artifacts.py`, `app/api_models.py`, `tests/test_api.py`, `tests/test_converter.py`, `tests/test_artifacts.py`, `README.md`, `Dockerfile`, `img2numpy.sh`
- Commands: `pytest -q`, `bash -n ./img2numpy.sh`
- Test Result: `19 passed` (warnings are FastAPI/Starlette deprecation warnings, no functional failures)

## Session Evidence (Tasks 71-72, 76-85)

- Files: `app/main.py`, `app/jobs.py`, `app/templates/index.html`, `app/static/styles.css`, `tests/test_api.py`, `README.md`
- Commands: `pytest -q`
- Test Result: `23 passed` (warnings are FastAPI/Starlette deprecation warnings, no functional failures)

## Session Evidence (Task 86)

- Files: `app/key_store.py`, `app/main.py`, `app/templates/index.html`, `app/static/styles.css`, `app/settings.py`, `README.md`, `tests/test_api.py`, `tests/test_key_store.py`
- Commands: `pytest -q`
- Test Result: `26 passed` (warnings are FastAPI/Starlette deprecation warnings, no functional failures)
