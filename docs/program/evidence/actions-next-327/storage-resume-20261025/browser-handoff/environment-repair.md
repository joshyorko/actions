# Exact browser environment blocker and narrow request

Observed 2026-10-25; no repair or privilege/security change attempted. This is an environment request, not published-candidate readiness.

| Item | Actual |
| --- | --- |
| Current user | agent UID/GID1000 |
| /usr/lib/chromium/chrome-sandbox | nobody:nogroup, UID/GID65534, mode4755 |
| Chromium-required system helper | root ownership (UID0), mode4755; diagnostic states this explicitly |
| System helper mount | read-only,nosuid,nodev |
| Process NoNewPrivs |1 |
| Process Seccomp |2, one filter; effective capabilities0 |
| Managed Playwright | package1.62.1; full Chromium and headless-shell revision1234, browser151.0.7922.34 installed |
| Managed chrome_sandbox | agent UID/GID1000, mode0700; not a configured setuid helper |
| Managed launch | both full browser and headless shell fail `No usable sandbox` with chromiumSandbox:true |

System helper owner repair alone is insufficient: read-only/nosuid mount and inherited NoNewPrivs prohibit using that setuid path. NoNewPrivs cannot be unset in descendants. Do not request a chown-only fix, disable the browser sandbox, remount this executor, change its seccomp profile, add capabilities, or clear privilege restrictions.

Smallest useful approval request to the environment owner: **provide a separate browser-only saved environment with a non-root user and supported Chromium user-namespace sandbox, pinned Playwright1.62.1/managed revision1234, using the documented narrow namespace-capable seccomp configuration.** Scope is a new browser qualification environment; no policy or ownership mutation in this executor, no second release writer, no credentials/tunnels/publication or Dakota dispatch. Playwright's documented namespace profile adds clone,setns,unshare capability to its baseline container seccomp policy; environment provisioning/approval belongs to the owner. Do not use privileged containers, unconfined seccomp, root browser or SYS_ADMIN as substitutes.

Owner must run browser-preflight.mjs with chromiumSandbox:true and obtain a real page title before starting acceptance. If that supported environment still fails, retain the new failure and escalate its exact policy boundary; do not broaden permissions automatically. Current evidence does not identify the exact host seccomp/namespace rule, so namespace-ready provisioning remains a proposed repair until preflight passes.

Then materialize exact a44 bundle Library libfile_b8db0ef755208191bd204e83f0d5a04d, bytes15679946, SHA25637ab0cf8bf66132c0112e5b65c7528a1092f4665ac7f7d32a022ec2ee77d18b0. Source d0c87a38a937cc339e8e661ac453c7a62ed41fa6; its browser directory pins a44/Corea6 while this historical directory retains original a42 identity. Rebuild target-local RCC preparation and fill only local path/preparation placeholders. Actual official host browser acceptance remains BLOCKED/NOT_RUN; Python client generated and Robot gates passed separately.

Primary documentation: https://docs.kernel.org/userspace-api/no_new_privs.html and https://playwright.dev/docs/docker#crawling-and-scraping. Documentation examples may use newer Playwright; retain candidate lock1.62.1 rather than silently updating it.

Upstream disposition: none. No permission denial occurred; the security-sensitive repair has not been attempted and requires owner provisioning approval.
