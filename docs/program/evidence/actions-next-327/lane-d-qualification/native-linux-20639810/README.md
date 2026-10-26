# Linux frozen/native qualification at 20639810

Source: freshly fetched integration head
20639810107cbe4b28e7f1acc5e2ac68bdde06b6, Runtime 1.1.0a40.
Independent archive/workspace: /workspace/lane-d/native-20639810.
No shared branch, workflow, version or production source edits. The canonical
build regenerated only tracked _static_contents.py (one line replaced); receipt
binds the generated file hash. 23 GiB free before; 22 GiB after. Existing prepared
RCC18.19.3 Doctor→Bootstrap→ToolkitTest toolchain reused; fresh package-local
Poetry environment installed this exact candidate lock.

## Commands

From isolated action_server, using these environment settings:

```bash
export PATH=/workspace/lane-d/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin:$PATH
export POETRY_CACHE_DIR=/workspace/lane-d/cache/poetry
export XDG_CACHE_HOME=/workspace/lane-d/cache
export ROBOCORP_HOME=/workspace/lane-d/robocorp
export npm_config_cache=/workspace/lane-d/cache/npm
export GOCACHE=/workspace/lane-d/cache/go-build
export GOPATH=/workspace/lane-d/cache/go
poetry install
poetry run invoke build-frontend
poetry run invoke build-executable --go-wrapper
poetry run python /workspace/lane-d/native-smoke/run_smoke.py
```

Frontend uses npm ci and canonical Runtime/Canvas builds, not CDN substitution.
No GHCR/publication/signing step. First Go build failed VCS stamping because the
archive had no Git metadata. Repaired only local metadata with git init, local
fetch of exact SHA, detached HEAD and read-tree; preserved generated files and
reran the unchanged supported build successfully. VCS stamping was not disabled.
The frontend archive run used its current timestamp fallback (1792939156), not
commit epoch. This is a source-bound native build, not a reproducibility claim.

## Actual artifacts and gates

- PASS: PyInstaller frozen bundle, 153 MiB directory:
  /workspace/lane-d/native-20639810/action_server/dist/action-server/
- PASS: Go wrapped executable, 99,336,469 bytes:
  /workspace/lane-d/native-20639810/action_server/dist/final/action-server
- PASS: direct frozen and wrapped `version` from /tmp, with Python environment
  selectors unset; both report 1.1.0a40. Wrapper update check disabled through
  supported ACTIONS_SKIP_UPDATE_CHECK=1; default wrapper extraction location used.
- PASS: direct frozen startup in separate empty directory, fresh SQLite datadir,
  task-local ROBOTS_HOME/ROBOCORP_HOME/cache, local fixture API key. HTTP root,
  /config and /openapi.json return 200; OpenAPI version is 1.1.0a40. Zero public
  action routes is expected with --actions-sync=false and no imported package.
- PASS: authenticated MCP resources/read of ui://action-canvas/v1/canvas.html
  returns bundled text/html;profile=mcp-app (485,423 response bytes). This exercises
  frozen Canvas bootstrap/renderer imports rather than reading source files.
  Server logs also show scheduler and MCP startup and clean shutdown.
- Bundle inventory includes libpython3.12, Work Items Python sources and native
  psycopg binaries. Inventory is not a claim every optional adapter was exercised.
- Windows/macOS: NOT_RUN. Browser rendering, generated backend/action execution,
  Linux image, shared PostgreSQL, signing and publication: NOT_RUN in this slice.

SHA256 frozen executable:
d5c2ce56a6bde29ea08a48a9c8345bff8596ac2efe652c96c594405112b428a8

SHA256 Go wrapper:
556622a3882724b6de0d3762a85a8086fbb055e242e9ae29a8b833196d733b1d

Full distribution file hashes/symlink targets retained in artifact-manifest.json.gz.
Local artifacts are retained, not uploaded. The directory bundle requires its
_internal directory; the Go wrapper embeds that bundle.

## Preserved failures and limits

The initial empty-directory smoke failed on read-only ~/.robots; using supported
ROBOTS_HOME resolved it. The initial harness cleanup hit ProcessLookupError after
child exit; stdout/traceback are retained and harness now handles that case.
The next startup correctly refused absent package.yaml; --actions-sync=false
selects the intended startup-only gate. /canvas/ returned 404 because Canvas is
an MCP resource; the final resource read qualifies that seam. None of these failed
attempts is counted as passing. No remaining blocker to this bounded Linux gate.

Canonical guide delta proposed to integrator: “Native builds from source archives
need exact detached Git metadata for Go VCS stamping; preserve generated frontend
delta and do not silently disable stamping. For empty-directory startup smoke,
set supported ROBOTS_HOME and --actions-sync=false, keep action execution separate,
and read Canvas via its authenticated MCP resource URI rather than an invented
HTTP /canvas route. Record both frozen-directory and Go-wrapper hashes.”

Learning/evidence: retained build failures, successful supported rebuild, actual
version and frozen MCP resource receipts. Uncertainty: no reproducibility proof,
no action execution/browser/native Windows/macOS pass. Upstream disposition:
none; observed prerequisites are local build/harness issues. No external report.
