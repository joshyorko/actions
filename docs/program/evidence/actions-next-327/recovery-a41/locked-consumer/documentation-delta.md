### Frozen-lock consumer qualification

A clean consumer install must use version constraints derived from the same
frozen Runtime `poetry.lock` as its candidate wheels, not an older handoff's
constraint file. Verify the frozen lock against the recorded source commit and
verify every input wheel against its retained digest before installation. Build
constraints from unique main-group distribution/version pairs; pass only the
explicit candidate wheel requirements to pip. A constraints file limits versions
without requesting platform-inactive or optional dependencies such as `duckdb`.
Do not convert all constraint lines into install requirements or enable undeclared
extras to make a graph check pass.

Retain pip's install report, `pip inspect --local`, `pip check`, exact lock and
constraint hashes, selected Runtime extras, and the qualifier implementation hash.
`qualify_consumer_inventory_327.qualify` runs in the prepared package toolchain so
its `packaging` dependency need not contaminate the candidate consumer. It checks
the active marker/extra-selected dependency graph, rejects versions outside the
lock and unexplained installed distributions, and treats pip alone as bootstrap
tooling. A successful pip resolver or `pip check` alone does not establish this
lock-consistent closure.

Compare installed files to the exact input wheel members, excluding only RECORD
because pip rewrites it; report full-wheel member counts separately from
package-only source-module counts. Assert import origins under the fresh consumer.
Use `action-server version` for the CLI identity probe: `--version` is not a
supported option. An in-process ASGI MCP initialize plus empty catalog can prove
basic SDK/Runtime compatibility without launching jobs, but does not qualify a
Canvas flow, selected execution provider, current Task protocol, or installed
recovery. Dependency closure and this smoke check do not establish full
vendor-independence or an independently generated SBOM dependency graph.
