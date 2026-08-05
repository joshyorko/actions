# Changelog

## 0.3.1 - 2026-08-05

- Fix the tag publication workflow to validate the package version without relying on an undeclared Invoke dependency.
- Supersede the failed pre-publication 0.3.0 tag; no 0.3.0 artifact was accepted by PyPI.

## 0.3.0 - 2026-08-05

- Harden attachment confinement, item-directory validation, and persisted-path checks against traversal and symlink escapes.
- Make SQLite reservation atomic and deterministic with immediate transactions, FIFO ordering, conditional claims, and rollback on errors.
- Preserve valid JSON payload shapes exactly and reject malformed stored JSON.
- Load Work Items privately in Action Server paths to resist project-root shadowing, and seed producer integrations from the server-owned datadir.
- Apply Ruff cleanup compatible with the Python 3.10 floor.
- Add the pinned Dev Container bootstrap and Poetry-based release gate, including strict artifact and clean-wheel alias/version checks.
- Publish complete PyPI documentation covering lifecycle, safety, compatibility, and backend boundaries.
- Redis and MongoDB/DocumentDB remain experimental pending service-backed reliability coverage.

## 0.2.4 - 2026-05-01

- Add `from actions import workitems` as a Robocorp-style module API for `workitems.inputs`, `workitems.outputs`, `item.done()`, and `item.fail(...)` workflows.
- Add `actions_work_items` as an import-safe alias for the hyphenated `actions-work-items` PyPI distribution name.
- Update producer-consumer templates and examples to use the module-shaped workitems API.
- Add regression coverage proving the Robocorp-style interaction loop works through the alias modules.

## 0.2.3 - 2026-05-01

- Add a Redis work item adapter for distributed queues, inline/file-backed attachments, queue stats, and orphan recovery.
- Add a DocumentDB work item adapter with MongoDB-compatible queue storage, GridFS-backed large attachments, queue stats, and file metadata cleanup.
- Add dynamic adapter loading and environment configuration helpers for selecting custom work item backends at runtime.
- Extend SQLite with environment-driven paths, input seeding, output queue creation, queue listing/stats, orphan recovery, normalized state/payload handling, and stricter file errors.
- Bump package version to 0.2.3.

## 0.2.0 - 2025-01-18

- Initial release with robocorp-workitems compatible API
- SQLiteAdapter for local persistent storage
- FileAdapter for Control Room JSON format
- Context manager pattern for automatic release
- Email parsing and glob file patterns
