# Development


## Requirements

- Python 3.12 or later
- invoke 2.2.0 or later

- `inv -l`

```
  build                  Build distributable .tar.gz and .wheel files
  build-executable       Build the project executable via PyInstaller.
  build-frontend         Build static .html frontend
  build-go-wrapper
  build-oauth2-config    Build static OAuth2 .yaml config.
  check-all              Run all checks
  check-tag-version      Checks if the current tag matches the latest version (exits with 1 if it
  clean                  Clean build artifacts.
  dev-frontend           Run the frontend in dev mode (starts its own localhost server using vite).
  devinstall             Install the package in develop mode and its dependencies.
  docs                   Build API documentation
  doctest                Statically verify documentation examples.
  download-rcc           Downloads RCC in the place where the action server expects it
  install                Optionally updates then also installs dependencies.
  lint                   Run static analysis and formatting checks.
  make-release           Create a release tag
  pretty                 Auto-format code and sort imports
  print-env
  publish                Publish to PyPI
  set-version            Sets a new version for the project in all the needed files
  test                   Run unittests
  test-binary            Test the binary
  test-not-integration
  test-run-in-parallel   Just runs the action server in dist/final/action-server 3 times in parallel
  typecheck              Type check code
```

- The `cloud list-organizations` CLI regression uses a deterministic HTTP-client response and synthetic credentials. It does not require a hosted Control Room account; use real credentials only when manually exercising a configured Control Room.
- To run individual tests: `python -m pytest tests/action_server_tests/mcp/test_mcp_integration.py::test_mcp_integration_with_actions_in_no_conda_mcp -v`

### Frozen managed catalog rollback acceptance

The frozen catalog control is now pinned to PR289 candidate `c78288c3` (tree `75a108db`) and measured Linux native build run 38053977419 attempt 1: synthetic merge `7421c8a4` has the same full Git tree as the candidate. Provenance artifact 11670088364 is 59,379,919 bytes with SHA-256 `2f441b87bb274db975ad3a1b57d3566f99d235bc3c5627c74c4e8782d5ace5c5`; its frozen executable is 17,604,776 bytes with SHA-256 `0e054d52dc56a2743874a49530745dd89b19c4342a8652ab3899e37822c66d7a`. Independent measurement verified the manifest, 1,188-entry inventory, package-tree digest, and wrapper artifact; receipt SHA-256 is `1ea75cefe71a5c45388b0696daabed804c748e8045c1499dab49d756593fc9d0`. Artifact provenance is separate from execution. Hosted run 38055229055 on control `57ba99ee` passed all ten Linux frozen cases (10 passed, zero failures/errors/skips, 257.83s). Independent review verified receipt artifact 11671465182, SHA-256 `ca81fb7da1915cde6bb4052b2effc1c6d5a871ee132db3e8c6ee8ff7efe7a404`, and the exact case set. This proves the selected Linux frozen lifecycle cases, not Go-wrapper execution, other platforms, or release completion. Before using this artifact from a later test/docs-only control commit, the workflow verifies the candidate/build tree and checks that Action Server source, Actions Core/HTTP Helper source, and their package/dependency lock inputs match the measured candidate. Any difference in those runtime inputs requires a newly measured native build. The previous f7 artifact remains historical. The 31239 byte review verified all 1,185 inventory entries (1,047 files and 16 symlinks), modes, contents, link targets, and full Git-tree equality. It verified the Go-wrapper source digest against Git blobs, and separately downloaded artifact 11665179231 (77,776,642-byte ZIP, SHA-256 `72c3451b5a9f1d54632d7bdeaf36aa0ab3b43e9fbf021497b53db372a00c80a8`) to verify the 81,977,186-byte wrapper binary digest `28cf80cb1d2811236ed64595b8b9d03a54d1904d63497eb39f34fb9bd67978f3`; that receipt did not execute the wrapper. Run 38042374430 on control 04fa0fea passed the four exact Linux frozen managed rollback/recovery cases on candidate 31239cf9 and build-source 056d3260 (4 passed, 0 skipped, 164.77s; artifact 11665938852, SHA-256 `ea9d0b0d7ed4b30e5b1ab7de4da869e4300a64ac6ac9229ae98226a8a33c83ff`). This proves those cases and controlled parent shutdown; it does not establish complete orphan census, frozen successful-generation drain, wrapper execution or release pairing. The managed fixtures pin Python 3.12, uv 0.9.26, and actions-core 1.0.2; each case checks the actual frozen parent and the managed worker's interpreter and Core origin. This proof is separate from source-mode pytest and the real-RCC provider rollback workflow.

The dependency-install step invokes Poetry from a `uv run` tool environment, so remove inherited `VIRTUAL_ENV` before `inv devinstall` to keep project dependencies in the Action Server Poetry environment. In the Go-wrapper job, capture `poetry env info --executable` before the acceptance step changes `HOME`; then run pytest with that exact interpreter while keeping the isolated wrapper HOME. Record the interpreter and pytest module origins before the suite. This avoids Poetry creating a fresh empty environment under the isolated HOME. The frozen-executable job can continue using `poetry run` because it does not replace HOME.

The successful-generation drain test was added as the fifth case in the frozen workflow. Hosted run 38050870256 passed all five cases against candidate 31239cf9 and its same-tree build 056d3260; it recorded the managed workers, v2 completion while v1 was blocked, v1's original result, and natural shutdown. This historical receipt does not cover the later catalog-ownership migration in PR289. The ten-case control adds all five multi-package sync CLI cases, including alias-capture rejection/recovery, and passed in hosted run 38055229055 against the measured c782 native artifact. Source-mode results and artifact provenance remain separate from that execution receipt. Run 38042374430 remains the separate historical four-case receipt. Do not infer frozen alias recovery from source-mode pytest or from the earlier candidate's five-case run.

The resource-owner history CLI case is selected as a separate eleventh node in the prepared control, covering concrete URI ownership across reload and restart. Frozen execution for that node is **NOT RUN**: the ten-case receipt above predates the resource-history implementation and does not cover it. Use a newly measured artifact bound to the final Runtime source/dependency inputs before claiming frozen acceptance.

The frozen-control workflow also defines a separate Go-wrapper job against the same measured candidate and eleven JUnit identities. It verifies the wrapper artifact's archive digest, single-member path, executable type and mode, and binary digest before extraction. A wrapper-job-only pytest plugin observes each selected `ActionServerProcess`: it verifies the launched Popen executable is the measured wrapper, its sole direct Runtime child is the cached measured frozen executable, and both identities have exited before normal test cleanup can signal anything. The per-node lifecycle receipt fails closed: a startup identity failure, missing verified child identity, or any stop/cleanup failure cannot be recorded as a natural exit. The original eleven test files and node IDs remain pinned; the plugin's per-node lifecycle receipt is a separate proof from JUnit. After the cases, the job also checks the extracted frozen executable. Its HOME, Actions home, Robots home, temp directory, JUnit, and receipts are independent from the frozen-executable job. This separate hosted gate remains **NOT RUN** until it completes successfully, and it does not replace or alter the frozen-executable receipt.

## Release process

To release a new version use `inv` commands (in the `/action_server` directory):

- 👉 Remember CVE cadence ando check the dependabot for items that can be fixed
  - Handle direct deps. in pyproject.toml 
  - Use `inv install --update` to bump the poetry.lock transient deps 
- First, check that the `CHANGELOG.md` is updated with the new changes (keep the `## Unreleased` section for the current release).
- `inv set-version <version>`: will set the version and update the `CHANGELOG.md` `## Unreleased` section to have the specified version/current date.
- Commit/get the changes (open a PR, merge it, get the contents locally).
- `inv make-release`: will create a tag and push it to the remote repository (which will in turn trigger the release pipeline).

## Beta releases

If for creating a normal release of version 0.0.1 you would need to create
a tag `sema4ai-action_server-0.0.1`, for creating a beta release you only
need to create a similar tag that ends in `-beta`, so it would be
`sema4ai-action_server-0.0.1-beta`. Pushing this tag will automatically
start a release pipeline that will build and upload to S3 the binaries.
Keep in mind that only one beta version can exist at a time and if you run
the pipeline again, it will overwrite the previous version.

In order to use the beta binaries, you can just download them directly.
For example this is the URL for Windows: `https://cdn.sema4.ai/action-server/beta/windows64/action-server.exe`
The name for the Linux and Mac binaries is just `action-server` and you can just replace
windows64 with linux64 or mac64 for the respective OS's. If you also need to
have a reference of what version was used, you can find the version file at:
`https://cdn.sema4.ai/action-server/beta/version.txt`
