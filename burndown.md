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
28. [ ] Define versioned API namespace and path pattern `/api/v1/{api_key}/{command}`.
29. [ ] Decide command names and semantics for v1 (`convert`, `batch`, `download`).
30. [ ] Add a central command-dispatch layer to route command handlers.
31. [ ] Implement `/api/v1/{api_key}/{command}` route scaffold.
32. [ ] Move single-file conversion logic into v1 command handler.
33. [ ] Return clear `404/400` responses for unknown or malformed commands.
34. [ ] Add command-level request validation models.
35. [ ] Document command grammar and reserved command names in a dedicated API reference section.
36. [ ] Define API key environment variables (`IMG2NUMPY_API_KEYS` or equivalent).
37. [ ] Implement secure key loading during app startup.
38. [ ] Implement API key parser/normalizer for configured keys.
39. [ ] Add constant-time API key comparison for auth checks.
40. [ ] Return `401 Unauthorized` for invalid or missing keys.
41. [ ] Add auth tests for valid key, invalid key, and missing key.
42. [ ] Document API key setup, storage, and rotation procedure in security-focused docs.
43. [ ] Define accepted input matrix for mixed batches (format + mime + extension).
44. [ ] Allow multiple uploaded files in one batch request.
45. [ ] Add streaming-safe upload reads for large requests.
46. [ ] Validate image payloads by decoding, not extension-only checks.
47. [ ] Support mixed-format batch conversion in a single request.
48. [ ] Add per-file conversion execution inside batch pipeline.
49. [ ] Add per-file result schema with status and error fields.
50. [ ] Implement continue-on-error behavior as batch default.
51. [ ] Add optional fail-fast flag for strict batch mode.
52. [ ] Add tests for mixed-format batches with all-valid files.
53. [ ] Add tests for mixed batches containing corrupted/invalid files.
54. [ ] Define `output_mode` contract for `link` and `npz`.
55. [ ] Implement artifact ID generation for saved outputs.
56. [ ] Create writable artifact storage directory in container/runtime.
57. [ ] Save single conversion result as `.npy` artifact when link mode is requested.
58. [ ] Save batch conversion results as `.npz` artifact.
59. [ ] Implement `/api/v1/{api_key}/download/{artifact_id}` endpoint.
60. [ ] Return direct download link payload when `output_mode=link`.
61. [ ] Return downloadable `.npz` response when `output_mode=npz`.
62. [ ] Add artifact metadata tracking (created time, size, expires time).
63. [ ] Add background cleanup job for expired artifacts.
64. [ ] Add environment-configurable TTL and storage limits.
65. [ ] Add tests for link generation, download success, and expiry cleanup.
66. [ ] Add converter option for output dtype casting.
67. [ ] Add normalization mode selector (`none`, `0..1`, `-1..1`).
68. [ ] Add channel mode selector (`RGB`, `RGBA`, `L`).
69. [ ] Add optional flatten/reshape policy for output arrays.
70. [ ] Expose all converter options in API request models and fully detailed docs with request/response examples.
71. [ ] Rebuild browser settings UI to control every conversion option.
72. [ ] Add browser batch UI controls for output mode and strict/fail-fast behavior.
73. [ ] Add request-size/file-count/timeout limits with explicit error messages.
74. [ ] Create `img2numpy.sh` as the primary build/install/update entrypoint with argument parsing, usage help, and command validation for `/build`, `/install`, and `/update`, and support an API port environment variable (for example `IMG2NUMPY_API_PORT`, default `8585`).
75. [ ] Implement and validate script overloads end-to-end: `bash ./img2numpy.sh /build -a` must perform a multi-architecture Docker build and push to `http://172.16.120.5:5000` as `img2numpy:latest`, plus support `bash ./img2numpy.sh /install -p <port>` and `bash ./img2numpy.sh /update -p <port>` where `-p` sets only the WebUI port and API port comes from env var/default (`IMG2NUMPY_API_PORT` or `8585`); then publish a fully detailed documentation set covering architecture, all endpoints/commands, auth, env vars, script usage, deployment, examples, and troubleshooting for external integrations.
