# Prepare the compiler on the tester host

The companion package.yaml is the exact 150-byte public contract from the tested
cloud compiler. SHA256:
`f3ed52dfc7933c242f50c94baaea50b42b04bc1f561523c357dd95a5054314f1`.
It pins Core a3 but only Python 3.12, not every transitive dependency. A fresh
platform/solver/cache may therefore produce a different artifact identity.

Original observed identities:
- specification: `sha256:185139c8765f507b913240020978796013b6d1a67d2de001815b8325397d7854`
- artifact: `sha256:23094fc1820262a768fd601f4964d633417fc2641f349666a5be55ab524f7598`
- Core wheel: `4147cdeb2a593e54194b4d2fcd2c92f0b029fb802d1d298e35c912a1fef03167`

Do not copy the old ROBOCORP_HOME, prepared.json, datadir or credentials. Obtain
Core's verified wheel through the parent's existing artifact handoff. If it is
unavailable, stop and report that prerequisite; a package version alone does not
prove the wheel bytes. These commands prepare a fresh trusted local cache; they
are not generated-code instructions and do not publish to a remote service.

Set absolute local paths before running, including the installed a38 interpreter
and its pinned RCC18.19.3 binary. `recipe` is this document's directory;
`compiler` is a new dedicated directory; `core_wheel` is the verified wheel.
Use a fresh bounded environment with at least 5 GiB free; monitor disk/log usage
and stop at the tester's agreed budget. Do not rebuild a broad workspace.

```sh
umask 077
mkdir -p "$compiler/robocorp/wheels"
cp "$recipe/package.yaml" "$compiler/package.yaml"
cp "$core_wheel" "$compiler/robocorp/wheels/actions_core-1.1.0a3-py3-none-any.whl"
sha256sum "$compiler/package.yaml" "$compiler/robocorp/wheels/"*.whl
export ROBOCORP_HOME="$compiler/robocorp"
export PIP_FIND_LINKS="$compiler/robocorp/wheels"
"$rcc" --version
"$rcc" env publish --environment "$compiler/package.yaml" --json --provider local \
  > "$compiler/publish.jsonl" 2> "$compiler/publish.log"
"$runtime_python" -I "$recipe/prepare-receipt.py" "$compiler"
```

Require both printed hashes above to match before publishing. Supply no extra
private indexes or credentials. Public dependencies still need the host's
approved network access; PIP_FIND_LINKS supplies the local Core candidate but is
not sufficient proof that the solver chose it. Verify actual installed Core
bytes inside the resulting artifact before using that compiler:

```sh
artifact=$("$runtime_python" -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["artifactDigest"])' "$compiler/prepared.json")
"$rcc" env exec --artifact "$artifact" --provider local --permissive-local \
  --trust-carrier "$compiler/robocorp/artifacts/v1/trust" \
  --trust-carrier-type filesystem --no-build \
  --inherit-streams --receipt-file "$compiler/core-exec.json" -- \
  python -I "$recipe/verify-core.py" "$compiler"
```

Use the explicit local trust carrier created by this host’s publish step, as the
Runtime adapter does. Omitting it caused `artifact trust attachment verification
failed` in the combined a39 manual probe; do not weaken trust policy or fabricate
attachments to fix that failure. The explicit permissive-local option is scoped to this owned synthetic unsigned
artifact. It does not change a trust store. verify-core.py compares every wheel
Python member with the artifact's installed files and tests isolated Data scan
context. The original cloud proof passed 52 members. Stop on mismatch; do not
patch an already published environment and retain its old identity.

Run qualify.py with explicit host paths:

```sh
ACTIONS_ACCEPTANCE_BASE="$installed_base" \
ACTIONS_ACCEPTANCE_PREPARED="$compiler/prepared.json" \
ACTIONS_ACCEPTANCE_EXPECTED_ARTIFACT="$artifact" \
ACTIONS_ACCEPTANCE_DIR="$new_fixture" \
  "$runtime_python" -I "$recipe/qualify.py"
```

installed_base must contain consumer/bin/action-server, the pinned installed
interpreter/packages and source-sha.txt with the verified Runtime source SHA.
The override pins the observed local artifact; it does not claim the original
23094... artifact was reproduced. If it differs, record this as a new local
compiler build and retain fresh full qualification evidence. Runtime wheel
identity remains independently pinned. Never edit the prepared receipt to
invent matching identities. qualify.py still checks package.yaml bytes and
Runtime source/version/origin, and records the actual compiler digest.

Verification here: exact source package hash, original preparation code and
52-member Core proof inspected; RCC18.19.3 publish/exec syntax checked with its
local help; portable receipt helper round-trip tested against a credential-free
copy of the observed publish result. No new cache build or tester-host execution
was performed by this handoff. Upstream disposition: none.
