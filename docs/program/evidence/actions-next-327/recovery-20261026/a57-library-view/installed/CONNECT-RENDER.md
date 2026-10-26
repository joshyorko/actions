# a57 CONNECT + RENDER

New candidate, separate from frozen Dakota a44.post2. Source bde511d2ba6318d0b100547cc6e777e53b9ebc80; tree58e3beed765765e13724928d26acefb729d8aeab. Linux x86_64 / CPython3.12, matching this wheel's target. Reuse the earlier verified target Python/platform setup.

Install the three bundled wheels in a NEW isolated environment using `constraints-connect-render.txt`. It pins the verified clean consumer's runtime dependencies by version without cloud-local file URLs. Run pip check. Keep a44's environment, datadir and evidence intact. Use a fresh absolute a57 datadir and empty working directory; this avoids cross-version database migration entirely. No compatibility with reusing a44 state is claimed by this handoff.

Use the already approved isolated local Runtime key/credential helper and existing test-plugin entry. This is a private Runtime API key, not an account password. Keep the key out of chat and receipts. Basic no-auth HTTP readiness does not enable native Canvas. Start only the new owned loopback endpoint. Preserve the working Executor and tunnels; add no OAuth, tunnel or cloud plugin.

Retest only authenticated discovery and a UI-only draft: `canvas_create` with title/idempotencyKey, `canvas_get`, `canvas_open`, then `canvas_get` for the same app. The app and library must render in the actual ChatGPT desktop host without the validation alert, with no action/tool execution controls enabled. Do not supply a backend, activate/release, invoke an action, qualify a compiler, or run restart/rollback tests. Record CONNECT and RENDER independently. Preserve a sanitized screenshot/result if rendering fails; clean up only the new owned endpoint and isolated test credential afterward.

Exact Runtime SHA25607a144f6200ea6bce8d52e14244aef2889e2c15cd52472a758381648fb693efa. Core8 SHA25642e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f. WorkItems2 SHA25672ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb. Embedded Canvas HTML490733bytes, SHA256753e9b50759cb628bf5a402575b33e2a411f4c3a775840146f6d507a05183b44. The manifest and static receipt carry these identities.

Source/component proof: captured app -> library ordering reproduced before the fix, complete Runtime frontend287passed, final Canvas203passed/1existing interchange skip, configured frontend quality passed. Clean339-member installation/METADATA and pip check passed. Cloud installed protocol/resource proof is separate. Actual ChatGPT owner retest remains PENDING; none of this is invoice E1 or full-release acceptance.
