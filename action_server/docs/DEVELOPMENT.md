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

The `Actions Runtime Frozen Catalog Rollback` workflow runs the duplicate public resource, template, and prompt-key rollback cases plus the watched malformed/recovery case against a hash-verified Linux frozen executable. Its current pin is native artifact 11664669288 from run 38039806634, built at synthetic merge `056d3260`; the Git API tree for that build source exactly matches candidate `31239cf9` tree `d2ef7229`. The workflow independently checks the candidate tree, build-source tree, server subtree, archive size and SHA-256, complete provenance inventory, package tree, and frozen binary. The previous f7 artifact receipt remains historical and is not used as current-source proof. The 31239 byte review verified all 1,185 inventory entries (1,047 files and 16 symlinks), modes, contents, link targets, and full Git-tree equality. It verified the Go-wrapper source digest against Git blobs, and separately downloaded artifact 11665179231 (77,776,642-byte ZIP, SHA-256 `72c3451b5a9f1d54632d7bdeaf36aa0ab3b43e9fbf021497b53db372a00c80a8`) to verify the 81,977,186-byte wrapper binary digest `28cf80cb1d2811236ed64595b8b9d03a54d1904d63497eb39f34fb9bd67978f3`; that receipt did not execute the wrapper. Run 38042374430 on control 04fa0fea passed the four exact Linux frozen managed rollback/recovery cases on candidate 31239cf9 and build-source 056d3260 (4 passed, 0 skipped, 164.77s; artifact 11665938852, SHA-256 `ea9d0b0d7ed4b30e5b1ab7de4da869e4300a64ac6ac9229ae98226a8a33c83ff`). This proves those cases and controlled parent shutdown; it does not establish complete orphan census, frozen successful-generation drain, wrapper execution or release pairing. The managed fixtures pin Python 3.12, uv 0.9.26, and actions-core 1.0.2; each case checks the actual frozen parent and the managed worker's interpreter and Core origin. This proof is separate from source-mode pytest and the real-RCC provider rollback workflow.

This workflow invokes Poetry from a `uv run` tool environment. Remove the inherited `VIRTUAL_ENV` before invoking Poetry, or Poetry can install project dependencies into uv's temporary tool environment instead of the Action Server virtualenv. Keep the pytest module/interpreter preflight under `set -e`, then run the suite with `poetry run python -m pytest`; a missing test module is an invocation failure, not a reason to fall back to host pytest or source-only tests.

Successful-generation drain is a separate source-mode test. It starts v2 while a v1 Run is blocked, proves the released old Run returns data from its immutable v1 snapshot, persists both Runs' results, and independently verifies natural child cleanup. Do not infer this behavior from malformed-reload rollback or from frozen catalog cases.

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
