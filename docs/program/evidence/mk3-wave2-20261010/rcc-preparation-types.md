# Fresh RCC preparation type verification

PASS on exact checkpoint `7eca36abce160b68f616eab9b7fdc9c4e7f2b053`, tree `2890ce916a5a9ee9201239635a220f95ecfe9ee8`: Mypy 1.20.2 reported **no issues in 326 source files**, exit 0, 10.748 seconds. Python 3.12.15 used the PR302 Runtime venv prepared through RCC Bootstrap. No correction to repository source is required.

After PR302's heavy run completed, execution entered the canonical pinned RCC 18.19.3 developer manifest using:

```text
rcc task script -r developer/toolkit.yaml --no-build -- python /workspace/work/actions-mk3-evidence/verify_rcc_preparation_types.py
```

The work-only harness required matching pyproject/lock bytes for Runtime, Core, HTTP Helper, devutils and Work Items, plus matching developer toolkit/setup files. It applied the exact subject toolkit's package_environment sanitization, then explicit absolute subject source paths. The child verified concrete Runtime/Core/Helper/Work Items/devutils module origins all resolved inside the 7eca checkout. It ran the package-declared full Mypy options from that checkout's action_server directory, with cache and evidence outside the source worktree:

```text
/workspace/work/actions-mk3-pr302/action_server/.venv/bin/python -m mypy --follow-imports=silent --show-column-numbers --namespace-packages --explicit-package-bases --cache-dir /workspace/work/actions-mk3-evidence/rcc-preparation-mypy-cache src tests
```

Initial provenance preflight exited before Mypy because the harness assumed namespace `devutils` had a non-null __file__. The corrected harness checks concrete `devutils.invoke_utils` instead. This was a harness issue, not a repository type failure. Both actual RCC invocation outcomes remain distinguished; no failed type check was relabeled successful.

The source worktree remains clean and no live owned command remains. No installs, source edits, actual RCC package metadata inspection or compiler advancement occurred. This verifies configured static source checking with the prepared interpreter; it is not a fresh Poetry package release-gate invocation. Historical preparation test and not-run receipts remain intact.

## Documentation improvement proposal

Add after the detached-checkout/prepared-Runtime paragraph in `docs/skills/repository-operations.md`:

> For a read-only type review using another checkout's prepared Runtime virtualenv, first compare the subject and prepared checkout's affected package manifests, lockfiles, and developer toolchain configuration. Enter the pinned manifest's existing RCC environment with `rcc task script -r developer/toolkit.yaml --no-build -- ...`, retain the toolkit's package-environment sanitization, and bind absolute subject source paths. Check concrete module origins: namespace packages such as `devutils` may have no `__file__`, so inspect an imported source module such as `devutils.invoke_utils`. Run the declared Mypy arguments from the subject package directory with a task-owned cache, and record the subject commit/tree, interpreter, Mypy version and origins. This establishes source type checking, not a fresh Poetry release gate or executed RCC package inspection.

Evidence: this successful exact-subject run, metadata SHA-256 inventory and concrete origin assertions in `rcc-preparation-types.json`, canonical toolkit package_environment, and RCC task-script help/execution. Ambiguity removed: origin checks that assume namespace __file__ and reuse of a prepared venv without explicit subject/dependency binding. Remaining uncertainty: actual bounded source-bound inspection and final-union hosted gates remain unexecuted.

Upstream disposition: none.
