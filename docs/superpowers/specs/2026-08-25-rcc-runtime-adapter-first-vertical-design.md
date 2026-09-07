# RCC runtime adapter: first execution vertical

Issue #134's first slice gives managed spec-v2 Action packages one RCC-owned
execution identity. The package's durable runtime descriptor contains only the
`rcc` kind, adapter contract, released RCC version, and exact `sha256:`
Environment Artifact digest. Local executable paths, materialization paths,
PIDs, and receipt paths are process evidence and are never descriptor
authority.

## Boundary

Import publishes the package environment with `rcc env publish --json`, parses
the exact artifact identity, and acquires it with
`rcc env acquire --json --artifact DIGEST --permissive-local`. Action discovery
and the existing preload process pool both execute through
`rcc env exec --artifact DIGEST --permissive-local`; pool workers add
`--inherit-streams --receipt-file UNIQUE_PATH` so RCC owns the wrapper lifetime.
The existing TCP preload protocol and pool remain the placement backend.

The package source directory and its `PYTHONPATH` are mutable execution input.
They are passed to import and worker processes but do not participate in the
artifact identity. A managed package never falls back to a host interpreter,
persisted `PYTHON_EXE`, Holotree activation cache, or another runtime when
publish, acquire, import, or exec fails. Packages without package.yaml retain
the existing unmanaged behavior.

RCC v18.19.2 starts `env exec` children in the materialized artifact directory;
the import adapter therefore passes the package source path explicitly to
`actions metadata` for discovery. The worker Action result is the authoritative
execution result: after a `PASS`, pool teardown may intentionally cancel the
persistent RCC wrapper, producing a receipt with `status: failed` and
`exitCode: -1`. That teardown receipt remains acceptable only after its exact
artifact digest, valid verification, and non-empty lease identity pass
validation.

## Provisional interfaces

`actions.server._rcc_runtime_adapter` owns strict JSON identity parsing,
typed descriptor serialization, publish/acquire preparation, command
construction, and the process handle's kill/wait receipt lifecycle. The
`ActionPackage.env_json` legacy column carries the versioned descriptor JSON
for this first slice; no schema migration is required.

## Out of scope for this slice

Source-only reload, atomic generation switch/drain, provider-dead warm reuse,
`rcc cache serve` A→B, corrupt/incompatible artifact rejection beyond the
command-boundary contract, and source/wheel/frozen acceptance remain explicit
follow-up proof tasks. No provider server, database, worker, Robot, UI,
Kubernetes, broker, or generalized adapter framework is introduced.
