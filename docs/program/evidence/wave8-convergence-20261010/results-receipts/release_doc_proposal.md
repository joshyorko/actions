# Canonical release-guidance proposal

**Target:** `docs/skills/repository-operations.md`, immediately after the Homebrew tap paragraph in the Runtime release section. This remains a read-only proposal; no source change was made.

> Homebrew Cask acceptance follows the Actions native release. The current `action-server` Cask covers Linux x86_64 and macOS arm64 only; Windows is a separate native asset. After a version’s native assets and verified hashes exist, update the tap through the `action-server-daily` slot or Tap Manual with `package_id=action-server` (`action=ci` then `action=release`), compare the Cask download hashes with the Actions release assets, and record clean install plus upgrade proof on each supported Cask platform. A Cask source update or green Actions release does not establish Homebrew consumer acceptance.

The live `joshyorko/homebrew-tools` main Cask is version 1.0.1 and binds Linux/macOS downloads to the same digests as the Actions Runtime 1.0.1 release. `auto-update-slots.json` maps `action-server-daily` to `action-server`; `tap-manual.yml` defines the CI and release actions. Runtime 1.0.3 native assets and Cask do not exist yet, so this consumer proof is pending. The current cask contains no Windows install stanza.

This adds a platform-specific consumer gate that is not explicit in the present release guidance. Keep the existing guide’s statement that Sema4AI/Robocorp handoffs are retired. Issue #211 still repeats those historical target names; update that issue’s criteria only when the issue owner handles its status.

**Evidence:** live GitHub API release asset hashes for `actions-runtime-1.0.1` and `action-server-1.0.1` match for both Cask platforms; current tap file blob IDs are recorded in `readiness.json`. PyPI JSON reports Core/Helper 1.0.3, Runtime 1.0.2, Work Items 0.4.4. The issue closure audit and later readback show #211 open and no 1.0.3 native publication.

**Remaining uncertainty:** No actual Homebrew install/upgrade proof was run for Runtime 1.0.3 because its native assets and cask are not published.

Upstream disposition: none.
