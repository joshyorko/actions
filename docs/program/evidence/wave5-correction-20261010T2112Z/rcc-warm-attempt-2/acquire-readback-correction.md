# Additive correction: recoverable B verification in the acquire tail

This supplements `interpretation.md` without changing the immutable attempt receipt or its original strict-gate status. The outer `env acquire --json` response is still incomplete: the 32 KiB ring tail omits its beginning, so the complete payload and `cacheHit` field cannot be parsed. The command returned exit 0, but the original gate's top-level `json.loads(stdout_tail)` correctly yielded no payload.

Independent review and local read-only reparse recover the complete nested final `verification` object from the tail. Its exact retained bytes hash to `04b03fb319022ad00e260fa46ce1be1c61b288aea26d88e5ca3faa7e436fb808`; it reports `valid: true`, policy `permissive-local`, and the same Artifact digest `sha256:d78a6bdc62558ab7d8b97df55fb3071eefe1c497bb8afe769490d8e324e86d16`. It is 594 bytes and is followed by the outer JSON closing bytes, consistent with a complete nested object at the end of the truncated document.

The retained consumer B state independently binds that digest and materialization:

- `task-work/consumer-home/artifacts/v1/materializations/d78a6bdc62558ab7d8b97df55fb3071eefe1c497bb8afe769490d8e324e86d16/ready.json`, SHA-256 `ea6c954caab0bf73a69d05e07396441e680f68bdd0fc48efda85aba24e482675`, has state `ready`, the exact digest, materialization ID `a2484ce_5a1fac3_e58fc530`, and a path under consumer B.
- Sibling `verified-content.json`, SHA-256 `8d4e32aaa51a8588cce1e7531da661492c7d8fe6d17a588ffa85955f137f2c28`, has state `verified-content` and the same digest, materialization ID, and path.

This corrects the earlier phrase that B verification could not be established: the verification object and retained local ready/content records are established. It does not recover the complete acquire JSON or establish its `cacheHit` value, and it does not establish an `env exec` outcome. The strict original attempt receipt remains `PREFLIGHT_OR_RUN_FAILURE`, because its planned top-level acquisition gate could not parse the complete result. The process/listener cleanup and no-retry statements in `interpretation.md` remain unchanged.

The recorded provider was `127.0.0.1:38593`; a read-only listener check after cleanup found no listener on that port. The new execution proposal uses this exact port for a task-owned 503-only counter if it is still free at launch; it must abort without touching another listener if binding fails.

The launch context also contains a SHA typo in `first_attempt_receipt_sha256`. It gives `5f26791b3808a157e1a8ac7866ca1b28ba493bda44e01ad57e2b9aec5ca358f1`; the frozen copied receipt actually hashes to `5f26791b3808a157a1e8ac7866ca1b28ba493bda44e01ad57e2b9aec5ca358f1`. The copied immutable receipt hash and its own receipt are authoritative; the launch-context file is preserved unchanged.
