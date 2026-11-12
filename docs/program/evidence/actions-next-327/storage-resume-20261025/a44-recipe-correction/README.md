# a44 recipe correction and official-host inputs

The original a44 Library bundle remains immutable and its product wheels remain unchanged. Its browser/qualify.py incorrectly asserted the older a42 source despite the bundled a44 configuration. Original bundle SHA256 37ab0cf8bf66132c0112e5b65c7528a1092f4665ac7f7d32a022ec2ee77d18b0; original recipe SHA256 6444546dfdbd8d271d046f9758c4addeb34e0eef4ae8bafc12d633c6153329c6. This is a delivered recipe defect, not a passed browser gate.

The corrected qualify.py SHA256 is 90d2ae610bd521a70785ef3bfb9238aa0719b12a8887c68d6a2d6aa4c5ae0f86. The focused reviewed patch changes the source assertion to d0c87a38a937cc339e8e661ac453c7a62ed41fa6 and two a42 display labels to a44. Independent AST/diff/config/wheel verification passed; no qualification execution occurred. Use a separate working copy of browser/ with this replacement after verifying its digest; retain the original bundle and recipe as failed evidence.

This correction is NOT a managed-CUA adapter. Importing or executing the qualifier creates synthetic key/fixture state and later grants and launches Playwright. Do not import it for preparation-only inspection. Those operations require the consumer's applicable authorization. The original sandboxed Playwright route and 5 GiB free-space floor remain unchanged. A managed-browser adapter must be separately reviewed and retain its distinct assurance scope.

## Obtain and build the official host

Official repository: https://github.com/modelcontextprotocol/ext-apps . Commit 82221c0c8ce7661efa6771c9d461511b1650495f (ext-apps2.0.3).

Archive: https://codeload.github.com/modelcontextprotocol/ext-apps/tar.gz/82221c0c8ce7661efa6771c9d461511b1650495f . Require exactly15,884,360 bytes and SHA25645bf48731a0fb23de541db12e6c3c7ed35fa52e55c8adbecea0b7cec95187733. Extract only ext-apps-82221c0c8ce7661efa6771c9d461511b1650495f/examples/basic-host into a fresh target-local host directory. Verify all16 original members against the bundle's browser/host-source-identity.json before replacing package.json. Copy browser/host-package.json and browser/host-package-lock.json as package.json/package-lock.json; this explicit packaging adaptation replaces workspace dependencies and adds pinned tsx, not unchanged upstream packaging.

With Node20.19.3 on PATH, from that host directory:

```sh
npm ci
npm run build
```

Both dist/index.html and dist/sandbox.html are required. The server command, only after separate launch authorization and Runtime readiness, is:

```sh
SERVERS='["http://127.0.0.1:REPLACE_RUNTIME_PORT/mcp"]' HOST_PORT=8080 SANDBOX_PORT=8081 node --import tsx serve.ts
```

Replace the port with the actual target-local Runtime port; this command is only the host server and does not supply Runtime authorization or prove UI acceptance. Canonical historical recipe path at commit6234f13ecf449b8df68092a10792ed2760393867: docs/program/evidence/actions-next-327/storage-resume-20261025/browser-handoff/README.md. Its a42 identities remain historical; use corrected a44 inputs here and the exact a44 bundle.

The producer rebuilt this exact public host:16 original source members verified, pinned npm ci and build PASS, no credential/grant/server/browser activity. host-build-receipt.json records output hashes and sampled allocation. npm build left two defunct esbuild children adopted by PID1; no live host process remained. This build does not establish browser acceptance.

## Measured storage and capacity decision

Producer measurements are allocations, not guaranteed consumer peak usage:

| Component | Observed allocation or enforced cap |
| --- | --- |
| Clean a44 installed consumer |193,896,448 bytes retained |
| Official archive/source/npm cache/install/build |201,228,288 bytes sampled peak at0.5-second intervals;1 GiB preparation cap |
| Retained a44 bundle and extracted transfer |15,679,946 bytes plus16,408,576 allocated bytes |
| Completed direct generated fixture |1,634,304 bytes retained; full browser fixture remains unmeasured |
| Target-local compiler preparation |2 GiB lane cap used by producer; historical peak not recorded, must be measured on target |
| Browser fixture |256 MiB cap;12 MiB log cap;5 GiB free reserve throughout |

A conservative fresh target plan allocates2 GiB for compiler preparation,1 GiB for host preparation,512 MiB for consumer/staging,256 MiB for fixtures, plus5 GiB remaining free:8.75 GiB initial free capacity. If strict Playwright browser installation is also required, reserve another1 GiB and request at least10 GiB free. This is a capacity plan, not a measurement of the full browser run. Account for all paths on their actual filesystems, shared quotas and competing workloads; root/tmp free space cannot be added if they share storage.

The parent reports maximum root/tmp free4.9 GiB and workspace2.3 GiB. Neither meets the original5 GiB floor even before preparation. Do not lower the guard. Smallest owner decision is an adequate existing writable volume/environment, or a separately reviewed managed-browser adapter with its own measured bounded storage design; the latter is not this strict recipe. The producer's10 GiB measurement floor applies to its own workload, not a newly imposed consumer rule.

Upstream disposition: none. Local packaging/recipe defect corrected; no external mutation.
