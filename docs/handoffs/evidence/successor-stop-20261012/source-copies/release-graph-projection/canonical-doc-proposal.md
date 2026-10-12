# Proposed canonical ledger insertion

**Proposed canonical file:** `docs/program/community-program-ledger.md`, immediately after “Published surfaces” and before “Immediate execution graph”. This is proposal text only; the immutable handoff was not edited.

```markdown
## Release boundary: one community Runtime 1.0.3 slice

Treat the 54 retained contracts as the full platform mission, not as one indivisible release checklist. The first release projection is one local/community Actions Runtime 1.0.3 slice paired with the already published Core/Helper 1.0.3 packages. Preserve every issue's full acceptance contract and state. This projection neither closes issues nor grants release approval.

Before shipping the affected Runtime surfaces, retain the explicit gates in #211 (Actions-side native handoff to the live community tap contract, actual asset/source/version/hash and external workflow verification, and an explicit decision about legacy CDN/S3 delivery); #208 (the released standalone Work Items defect, real packaged backend behavior, and remaining UI/error/accessibility criteria); #151, #152, and #153 (source-import safety, configured administrative authorization, and browser Origin/WebSocket policy); #195 (clean installed Runtime-wheel compatibility across the versioned Core boundary); #96/#97/#98 (existing-product route and state compatibility, accessibility, and complete embedded/frozen artifact validation); and #125 (community-only templates and public dependencies). Keep #212's installed Runs/UI defect on the release disposition list until its exact artifact impact is reproduced and either fixed or explicitly shown not to ship in the candidate. A bounded subgate or merged implementation is not whole-issue acceptance.

For this local slice, retain SQLite as the zero-configuration backend and verify the source/wheel/frozen forms that are actually shipped. #84's PostgreSQL multi-runtime, migration-race, and rolling-upgrade matrix belongs to the later split-runtime support contract unless the 1.0.3 support statement promises PostgreSQL. #134 may deliver its explicitly bounded local RCC consumer proof; it does not require PostgreSQL, remote workers, Package v3, or a second adapter, and does not satisfy the full RCC provider/lifecycle contract.

Keep later platform delivery in its existing contracts: immutable Package/Deployment identity and compilation (#129/#130/#135/#136/#148), durable Run/Attempt leases, outputs, bindings and review (#83/#86/#87/#92), independent workers and adapter/placement conformance (#90/#133/#138/#139/#142/#143), MCP Tasks, Robot Tasks and durable Work Items (#85/#132/#144), providers and exposure lifecycle (#131/#196/#214), Canvas renderer/authoring/templates (#71/#99/#100/#127), and the Control Room, CLI and workflow product (#145/#146/#147/#141). These remain part of the 54-contract mission; their open states alone do not block the local 1.0.3 slice.

#210 is the already accepted retained closure for the HTTP helper credential-delivery contract. Preserve its recorded status and do not republish or replace the existing helper artifact. Keep the separate future credential-safe CI delivery requirement distinct from that accepted closure. #162/#194/#209 are narrow close-ready recommendations pending owner confirmation, not release blockers absent an explicit contract relation. Keep #293–#296 human-held and undispatched; #279 is outside the retained graph.

The strategic roadmap/policy request in #155 needs an explicit owner disposition: decide whether compatibility and experimental-adapter policy is a pre-release gate or a follow-on documentation obligation. Do not infer that decision from its open state or advisory-origin bucket.
```

## Why this change is durable

The source matrix is a read-only reconciliation observed at 2026-10-10T22:44:44Z, not a live GitHub refresh. It retains 53 open graph members and #210 as the sole closed member. Its operational buckets are explicitly bookkeeping categories, not release semantics. This insertion documents a release overlay while leaving each retained contract, acceptance hash, raw state, typed relation, and the 5 non-retained rows intact.

## Evidence boundary and unresolved decisions

The immutable handoff at `0d5424ee8ec7c0a0ccea42a91eeecea144aa2934` says Core/Helper 1.0.3 registry/API proof was retained; Runtime PyPI 1.0.2 and native/Cask 1.0.1 remained current at the recorded cutoff; Runtime 1.0.3 publication, downloads/checksums, Homebrew installation/upgrade, and actual ChatGPT acceptance were unexecuted. It also records RCC code GO_COMPONENT only and actual metadata NOT RUN. Therefore this proposal describes gates and boundaries, not achieved results.

`#84` support-policy scope (SQLite versus PostgreSQL), `#134` exact local RCC release gate, `#155` roadmap timing, and whether #195's clean installed-wheel proof must precede every Runtime 1.0.3 package remain owner decisions. The full acceptance remains authoritative until each is resolved.
