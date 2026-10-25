# Initial clean a38 installed qualification: FAIL retained

Exact source 4babd01c3ffd4728633b565aadae346e5b98b087 built from a clean Git
archive through the pinned RCC toolkit. Both frontend entrypoints were rebuilt
with npm ci from the committed lock, public OAuth catalog only, and measured
pinned RCC. Clean noneditable install, pip check and isolated import passed.
Runtime wheel SHA256 a9f5c7841ed9aeb1d4684e2dfa409a2a05667f7d7598e0a453ef01647a71064a.
Core a3 and Work Items 0.5.0a2 exactly matched their prior measured wheels.

The first actual MCP client attempt used unsupported Canvas field type `number`;
the bounded public API rejected it. The corrected fixture uses `integer` and
successfully compiled/imported/tested/activated both Actions in one Package.
Its public offline authorize-local step then failed: it used the legacy
single-capability registry.load and rejected the bundle. No Tasks executed.
Both receipts remain FAIL; this artifact is not a qualified candidate.

The production fix uses load_verified, which integrity-verifies either retained
single or bundle format. The entry-boundary regression first failed as expected;
all29 local-authorization tests subsequently passed, zero skipped. Exact source
and installed requalification follow in a separate checkpoint. XML originals
are retained as base64 with decoded hashes. No private datadir, session, key,
source-provider credentials or bulk fixtures are published.

Upstream disposition: none.
