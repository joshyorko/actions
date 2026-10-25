# Ordinary a38 managed consumer: cross-VM input inventory

This handoff is independent of Robot. Source inspection completed against PR328
`5b16289da3d0f45f3d2534a4abf29fb1e3a9463e`; no wheel rebuild, server launch,
credential transfer, or fresh-VM acceptance is claimed here.

## Existing credential-free inputs (reuse, do not reconstruct)

Paths below are relative to `docs/program/evidence/actions-next-327/`:

| Input | Committed path |
| --- | --- |
| Exact-source wheel build recipe | `recovery-a38/installed-qualified/build-installed.py` |
| Source and generated-input hashes | `recovery-a38/installed-qualified/build-inputs.json` |
| Recorded wheel trio hashes | `recovery-a38/installed-qualified/wheels.json` |
| Consumer dependency constraints | `recovery-handoff-20261025/extension-handoff/dependency-constraints.txt` |
| Portable Core a3 manifest | `recovery-core-a3/rcc/package.yaml` |
| Real isolated Core wheel-member verification | `recovery-core-a3/rcc/verify.py` |
| Earlier Core RCC proof and its boundaries | `recovery-core-a3/rcc/README.md`, `core-proof.json` |
| Ordinary managed consumer and SAME-state restart procedure | `recovery-a38/managed-installed-consumer/README.md`, `qualify.py` |

The exact Runtime build source is
`f332a8284e78844abcf6700a600d2891d742b682`, not the current release tip.
That commit already contains the portable manifest, whose SHA256 is
`f3ed52dfc7933c242f50c94baaea50b42b04bc1f561523c357dd95a5054314f1`.
Its bytes name `actions-core=1.1.0a3` and `python=3.12`, with no local wheel URL,
credentials or authorization identity. The Python range and transitive resolution
are not a complete environment freeze.

Recorded wheels (compare actual bytes; never label a different rebuild identical):

- Runtime1.1.0a38: `103c53cf3b960fe173d6fa53485e097267a071684bc464214739b660a4c33203`
- Core1.1.0a3: `4147cdeb2a593e54194b4d2fcd2c92f0b029fb802d1d298e35c912a1fef03167`
- Work Items0.5.0a2: `72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb`

## Exact-source build instructions

Use a fresh isolated checkout of the exact source above. Preserve any existing
checkout; do not reset a tester's working tree. Verify `git rev-parse HEAD` and
clean tracked state before building. Use Josh RCC18.19.3, writable task-local
ROBOCORP_HOME/ACTIONS_HOME/ROBOTS_HOME and caches, and at least 8GiB free.
Run Doctor -> Bootstrap -> ToolkitTest using `developer/toolkit.yaml`.

Read the committed `build-installed.py` before running it. It archives its ROOT
HEAD, attaches that exact Git metadata, rebuilds both frontend entrypoints from
the archived npm lock, builds public OAuth catalog data, builds Core/SDK/Runtime
wheels via Poetry, creates a clean noneditable consumer with the committed
constraints, runs pip check and verifies isolated Runtime origin/version.
It does not pin HEAD itself: the exact checkout precondition is required.

The recipe is machine-local: ROOT defaults to `/workspace/actions`, BASE to
`/workspace/actions-327-a38/installed-fixed`, and its final origin assertion uses
that BASE literally. To relocate, copy the script outside the checkout and change
only those ROOT/BASE literals and the matching final origin assertion. BASE must
not exist. Invoke that copy through:

```sh
rcc task script -r developer/toolkit.yaml -- python /owned/path/build-installed.py
```

The recipe requires the pinned bundled RCC asset at
`action_server/src/actions/server/bin/rcc-18.19.3` in ROOT. Verify Linux x86_64
SHA256 `7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428`
against `build-inputs.json`; use the repository's pinned acquisition workflow.
No latest-RCC or host pip fallback. Preserve build/install reports and measured
wheel hashes. A different rebuild hash is new evidence, not reproduction of the
historical wheel. No public package publication is needed.

## Locally prepared RCC environment

The existing `PreparedRccEnvironment` is local preparation evidence: it contains
an absolute `robocorpHome`. Copying its JSON to another machine does not copy the
artifact store or establish trusted preparation. Do not copy private Runtime
state, network profiles, signing material, or authorization receipts.

On the target, create a new private preparation directory containing the exact
portable manifest and a new `robocorp/wheels` directory. Stage only the measured
Core wheel there (the recorded hash above if reproducing that candidate). Use
real RCC to publish to the local provider:

```sh
ROBOCORP_HOME=/owned/compiler/robocorp /verified/rcc-18.19.3 env publish \
  --environment /owned/compiler/package.yaml --provider local --json \
  > /owned/compiler/publish.json 2> /owned/compiler/publish.stderr.log
```

Use the installed a38 interpreter to parse the result with
`parse_published_artifact_details` from `actions.server._rcc_runtime_adapter`.
Create the local receipt with the actual specification/artifact digests and exact
manifest byte digest:

```python
import hashlib, json
from pathlib import Path
from actions.server._rcc_runtime_adapter import parse_published_artifact_details
from actions.server.deployments.package_revision_compiler import (
    PreparedRccEnvironment, RccBuildIdentity,
)
base = Path('/owned/compiler')
published = parse_published_artifact_details(json.loads((base/'publish.json').read_bytes()))
prepared = PreparedRccEnvironment(
    robocorp_home=base/'robocorp',
    package_yaml_digest='sha256:'+hashlib.sha256((base/'package.yaml').read_bytes()).hexdigest(),
    build_identity=RccBuildIdentity(published.specification_digest, published.artifact_digest),
)
(base/'prepared.json').write_bytes(prepared.to_receipt_bytes())
```

Do not hand-format the receipt: the loader requires canonical bytes.
Before accepting it, run the existing `recovery-core-a3/rcc/verify.py` through
actual RCC `env exec` with `python -I`, changing only its local `base` path in a
separate copy. It checks all installed Python members against the staged wheel,
not merely the version. Use Runtime's `build_exec_command` with
`RccRuntimeDescriptor(artifact_digest=..., provider_reference='local')`, a real
receipt file, and `local_trust_carrier=base/'robocorp/artifacts/v1/trust'`.
Set ROBOCORP_HOME to that same home and RCC_NO_BUILD=1; preserve stdout/stderr
and verify the returned receipt with `read_receipt(receipt_file, artifact_digest)`.
This uses the existing adapter's explicit filesystem trust carrier; do not disable
verification or manufacture a receipt. Fail closed if the real child/receipt fails.

## Historical identity gap and local qualification

The original managed consumer pins artifact
`sha256:23094fc1820262a768fd601f4964d633417fc2641f349666a5be55ab524f7598`.
The committed earlier Core manifest/prepared receipt instead records artifact
`sha256:a8464ce6d65b33577b262f740c6a4cd4a0e3e8d958a44c3685224e4c7548f21a`.
The a38 canonical README reports the former artifact and same measured Core wheel,
but does not supply its exact adjacent package.yaml digest, resolved freeze, or
portable artifact export. These two artifact identities must not be conflated.
The old prepared.json is a reference receipt, not a transferable environment.

The currently assigned desktop gate requires that exact historical artifact.
Do not replace its digest assertion with the older artifact or a newly built one.
The local preparation steps above describe the supported mechanism only; they do
not reconstruct the missing exact inputs or satisfy this gate.

The producer/integrator must supply, after confirming the identity:

1. Exact credential-free `/workspace/actions-327-a38/compiler/package.yaml` bytes
   and SHA256 matching the original prepared receipt's packageYamlDigest.
2. The original preparation's specificationDigest/artifactDigest/RCC version and
   resolved freeze or portable artifact export needed to reproduce/import the
   exact `23094fc...` identity. The producer's absolute robocorpHome is descriptive
   only and must not be treated as a portable path.
3. Exact measured Core wheel selection and preparation commands, including any
   portable dependency freeze that differs from the older committed manifest.

Both `/workspace/actions-327-a38` and `/workspace/actions-recovery-327` are absent
in this lane VM. The committed a38 JSON/recipe/README search exposes the digest
and source/wheel facts but not the adjacent exact compiler manifest/receipt.
This is a missing-producer-input blocker, not a denied action or an upstream bug.
No private datadir, authorization receipt, credentials or whole home is requested.
The original qualified script and historical digest assertion remain unchanged.

## Local authorization and handoff limits

The local harness generates a fresh synthetic key in memory and a fresh private
datadir/profile. It reads the local bootstrap owner, then explicitly invokes public
`authorize-local --dry-run`, binds expected_grants_digest, applies and verifies
replay. Exact-deployment authorization occurs while the Runtime is stopped. Those
steps must run on the target; copying the producer's grants, owner IDs, profile,
datadir, API key or authorization result is prohibited. The recipe stops all
servers; an interactive tester must preserve the same local state and credential
privately at the documented pause boundary rather than reconstruct a fixture.
Only screened, credential-free evidence may leave the VM. In particular, the
recipe's `*-authorization.json` output files are local authorization receipts;
exclude them from any transfer even if they contain no bearer value.

No new service qualification was executed for this inventory. Required target
proof remains ordinary installed real RCC execution, managed completion and replay
after restart of the same state. This is not Robot, retry, Task, or extension UI
proof. The canonical Robot adapter contract request remains active.

## Exact canonical guide delta for integrator

Append to the existing prepared-RCC guidance in `docs/skills/repository-operations.md`:

> Cross-VM managed-consumer qualification requires exact source-built wheel
> provenance, portable package.yaml bytes, a locally verified RCC artifact and
> canonical local PreparedRccEnvironment receipt. A producer-local prepared.json
> does not transfer its artifact store. Keep historical and newly prepared
> artifact digests distinct, verify installed Core members through real RCC, and
> perform public offline owner/deployment authorization on the target. Do not
> transfer profiles, datadirs, credentials or authorization receipts. Rebuilding
> from a Python range is not proof of reproducing a historical artifact digest.

Evidence: committed build recipes, manifest hash, two distinct recorded artifact
identities, PreparedRccEnvironment serializer/loader and managed qualification
script. No stale claim removed; cross-VM and exact historical reproduction remain
unverified. Upstream disposition: none.
