# Final review: sealed filesystem output reader

Reviewed the dirty `filesystem.py` and `test_filesystem_recheck_327.py` in
`/workspace/actions`, against
[`filesystem-fix-review-luna.md`](filesystem-fix-review-luna.md). This was a
read-only review. I did not modify source, tests, or canonical documentation,
and did not rerun tests. The supplied `/tmp/327-filesystem-final.log` records
the focused command completing with **24 passed in 0.42s**.

## Findings

**No remaining correctness blocker found.** The earlier cursor-loss finding is
fixed: `_Reader.read()` derives a local position from `remaining`, collects and
verifies every requested block, runs the final descriptor identity check, joins
the result, and only then decrements `remaining` (`filesystem.py:93-123`). Any
read, digest, or identity exception before that commit leaves the logical cursor
unchanged. The new spanning-read regression tampers the second block, confirms
the spanning call raises, restores that block, then asserts the next read returns
the entire original payload (`test_filesystem_recheck_327.py:151-164`). This
covers the state-loss scenario from the prior review.

The content-integrity boundary remains sound on inspection. `open()` measures
the supplied whole-object SHA256 and captures one SHA256 per 64 KiB block before
yielding a reader (`filesystem.py:278-305`). Each `read()` uses positioned reads
to assemble every touched complete block, checks its digest against the
open-time value and checks descriptor identity, then returns only the requested
slice (`filesystem.py:97-120`). This catches same-size rewrites even if timestamp
observations are masked, including rewrites to a block already partially read;
the regression file covers first-byte, unread-block, and same-block cases. Short
positioned reads are accumulated. Empty, partial, cross-block, EOF, and invalid
read-size behavior is covered by the supplied focused suite.

Resource use has fixed bounds from this implementation: objects are capped at
64 MiB; open-time verification holds one 64 KiB block plus at most 1,024
32-byte block digests; a read verifies touched blocks of at most 64 KiB each.
A single `read(-1)` may retain the requested result slices while joining the
returned object, so peak result memory can approach twice the object size. The
production output transport reads in 64 KiB chunks (`run_outputs/transport.py:92-99`),
and the inspected internal bounded-read consumers request fixed limits or loop
over bounded chunks. Each call intentionally re-reads and hashes a complete
touched block, so repeated tiny reads can amplify I/O up to one block per call;
that is the cost of detecting a rewrite after earlier partial reads and is not
an unbounded allocation. I found no current consumer that turns this into an
unbounded single-request read.

Platform and descriptor guards are preserved. Non-Linux fails before feature
resolution or descriptor allocation; `pread` is resolved as callable during
provider initialization before the root descriptor is duplicated, and absence
or a non-callable value fails closed (`filesystem.py:145-160`). The supplied
regressions verify both missing and non-callable `pread` leave descriptor count
unchanged and the caller-owned directory descriptor usable. Procfs, `O_PATH`,
`O_NOFOLLOW`, regular-file, size, link-count, and sealed-mode checks remain in
place. API behavior stays a bytes-returning `read(size=-1)` with the usual
bounded cursor semantics, and the failure behavior is now all-or-nothing for
cursor advancement.

## Canonical documentation proposal

No canonical documentation was edited in this read-only lane. Extend the
existing sealed-output paragraph at
[`repository-operations.md:5161`](../actions/docs/skills/repository-operations.md)
with this exact text after “sealed output authority.”:

> The Linux filesystem provider verifies each complete touched 64 KiB block against digests measured when the object is opened, then advances the reader cursor only after all requested blocks and the final descriptor-identity check succeed. A failed read returns no bytes and leaves the cursor unchanged. Objects are capped at 64 MiB, `pread` is required at provider initialization, and the output transport requests 64 KiB chunks.

Evidence: `filesystem.py:21-22,39-43,88-123,145-160,278-305`; regression
coverage in `test_filesystem_recheck_327.py:151-164` plus its partial-read,
tamper, short-read, and capability cases; transport behavior at
`transport.py:92-99`; supplied test receipt at `/tmp/327-filesystem-final.log`.
This captures implemented behavior and makes the failed-read cursor guarantee
explicit. No stale or ambiguous canonical claim needs removal. Remaining
uncertainty: I did not independently rerun the supplied suite or check other
platforms, as instructed.

## Receipt

Upstream disposition: none. The reviewed behavior and fix belong to this
Actions implementation; no upstream defect was found and no external target was
authorized.

Documentation improvement:
- Canonical file changed or proposed: propose the exact paragraph above for `actions/docs/skills/repository-operations.md` after line 5161.
- Durable learning captured: full touched-block verification is measured at open and rechecked per read; cursor advancement commits only after all data and identity checks succeed; the Linux provider requires `pread` and the output transport reads in 64 KiB chunks.
- Evidence: implementation lines and regression/log references listed above.
- Stale or ambiguous guidance removed: none identified.
- Remaining uncertainty: focused tests are supported by the supplied log, not independently rerun; no cross-platform behavior was checked.
