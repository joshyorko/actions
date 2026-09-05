# Build System Tests

Unit tests for the repository-owned Action Server build validation helpers.

Tests cover:

- PackageManifest validation
- frontend dependency-source resolution
- built-import detection
- BuildArtifact metadata generation

Run them from `action_server/` with:

```bash
poetry run pytest tests/build_system_tests -q
```
