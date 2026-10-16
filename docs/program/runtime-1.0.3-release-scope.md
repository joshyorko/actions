# Runtime 1.0.3 supported release scope

This candidate freezes the tested local Runtime subset. Publication remains unverified until the release gates and external readback pass. It does not accept or close the 54-contract execution graph, #82, or #101. The source and publication receipts determine release status; a prepared changelog section or green PR publisher does not establish publication.

The production support target is limited to the measured Linux x86_64, macOS arm64, and Windows amd64 profiles, with Python 3.12/3.13 wheels and the pinned RCC v18.19.3 baseline. Preserve these implemented behaviors:

- Local Python Action packages served through HTTP and the current stateless MCP contract, using the published Core/Helper dependency boundary.
- Local SQLite administration, Run History summary pagination, explicit Run details, and reconnect invalidation. Pages are capped at 200 rows; search covers loaded pages. Legacy full-detail responses keep their existing payload behavior.
- Current Work Items UI list/detail/storage and bounded browser states. Worker state transitions, attachments, distributed queues, and adapter lifecycle acceptance remain separate.
- Configured bearer authentication and the tested browser-session/exact-Origin controls. Local no-key use is limited to trusted loopback deployments. A browser cookie does not authorize MCP. Externally hosted TLS/proxy arrangements need their own deployment qualification.
- Robot ZIP import, cataloging, default task execution, and existing diagnostic logs under trusted service-owned root, ancestor, and temporary namespaces. Robot request-input forwarding and canonical workload artifact retrieval are known limitations, independently reproduced on this candidate in #315/#316 and targeted for 1.0.4.
- Operator-owned custom OAuth applications through private `--oauth2-settings`, with a registered nonblank client ID, appropriate endpoints and redirect URI, and client-secret exchange or supported S256 PKCE. The community public catalog intentionally supplies no hosted registrations. Unsupported hosted modes must fail closed. Configured-key browser-session management of the protected OAuth routes remains limited; do not advertise a seamless UI flow for that mode.

Experimental or unqualified features remain outside production support:

- Robot remote-URL import, hostile concurrent local namespace writers, and unqualified Windows staging ACL isolation.
- Canvas authoring/execution and optional host projections, split replicas/PostgreSQL/worker topology, durable MCP Tasks and human-review workflows, immutable Deployment/Package Revision architecture, and a general second-adapter contract.
- RCC provider/artifact-backed execution, offline-warm reuse, lease/recovery qualification, and all newer RCC upgrades. Ordinary source tests and the v18.19.3 toolkit matrix do not qualify those contracts.
- Full-route/manual accessibility, non-Chromium browser coverage, and broader deployment/provider matrices beyond retained bounded receipts.

Optional PRs #306 and #313 are deferred because their exact-head green CI does not close their specialized dependency/cleanup gates. PRs #305 and #308 are also deferred. No optional PR is admitted to this release.

Homebrew handoff remains separately tracked in #211. Publication requires the reviewed community merge, exact version/source verification, an unused immutable `actions-runtime-1.0.3` tag through the existing guarded release helper, successful PyPI/native tag workflows, and external artifact/hash/installation readback. Never retag or replace published distributions to repair a failed release; use recovery only when its exact guarded contract applies.
