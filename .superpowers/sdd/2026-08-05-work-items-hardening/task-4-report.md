# Task 4: Persistent backend release gates

## Fix round 3

The in-container `verify-work-items` gate no longer invokes Docker. It requires explicit Redis and MongoDB endpoints and runs the complete Work Items suite, including the mandatory service marker. GitHub Actions now owns Compose startup and teardown on its Ubuntu host. The Bluefin path is `.devcontainer/bin/smoke-host`: it starts Compose on the host, attaches the Dev Container image to the named service network, passes service-DNS endpoints, supports linked worktrees by mounting the common Git directory read-only, and always removes services, volumes, and orphans. No Docker socket is mounted.

The first real host smoke exposed a MongoDB timestamp-precision race in the service regression: a zero-minute strict cutoff could equal the newest BSON millisecond timestamp. The regression now places the recovery cutoff strictly after both reservations, so it tests recovery deterministically.

## TDD evidence

RED:

```text
python -m unittest discover -s .devcontainer/tests -p test_service_orchestration.py -v
Ran 3 tests: 1 failure, 2 errors
```

The host wrapper did not exist, and the verifier reached `poetry` instead of rejecting absent endpoints.

GREEN:

```text
python -m unittest discover -s .devcontainer/tests -p test_service_orchestration.py -v
Ran 3 tests in 0.042s: OK
```

The shell regressions execute the wrapper with a recording Docker fake and prove network/endpoints, cwd independence, success cleanup, failure cleanup, and required in-container endpoints.

## Verification

```text
bash -n .devcontainer/bin/smoke-host .devcontainer/bin/smoke .devcontainer/bin/verify-work-items: passed
python -m unittest discover -s .devcontainer/tests -v: 10 passed
docker compose -f work-items/tests/compose.persistent-backends.yaml config: passed; named default network resolved
docker build -t actions-devcontainer:test .devcontainer: passed
.devcontainer/bin/smoke-host: 61 passed; Ruff, Poetry lock check, build, strict Twine, wheel metadata/imports, and git diff check passed; Compose teardown removed both containers and the network
git diff --check: passed
```

The first host smoke failed with `1 failed, 60 passed` at MongoDB orphan recovery and still removed containers and the network. After making the cutoff deterministic, the complete host smoke exited 0.

## Documentation improvement

Documentation improvement:
- Canonical file changed or proposed: propose updating `docs/skills/work-items.md`; this isolated lane did not edit canonical docs.
- Durable learning captured: replace the host `docker run ... .devcontainer/bin/smoke` example with the cwd-independent host command `.devcontainer/bin/smoke-host`. State that the wrapper owns Compose lifecycle, joins `actions-work-items-persistent-backends_default`, passes service-DNS endpoints, mounts linked-worktree Git metadata read-only, and performs volume/orphan cleanup without mounting Docker access. State that `verify-work-items` requires `TEST_REDIS_URL` and `TEST_MONGODB_URI`, never orchestrates Docker, and always runs service tests. Record `pytest tests -q -m 'not persistent_backend_service'` only as an ordinary diagnostic command, never a release/smoke gate.
- Evidence: shell integration regressions in `.devcontainer/tests/test_service_orchestration.py`; successful real `.devcontainer/bin/smoke-host` run with 61 package tests; workflow Compose trap and endpoint environment; successful Compose config resolution.
- Stale or ambiguous guidance removed: remove the direct host `docker run` command that provides neither reachable backend services nor a Docker socket, and remove wording that implies `verify-work-items` starts its own services.
- Remaining uncertainty: GitHub-hosted execution was not run locally; its Compose lifecycle uses the same validated Compose file and endpoint contract.
