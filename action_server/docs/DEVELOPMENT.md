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

The `Actions Runtime Frozen Catalog Rollback` workflow is intended to run the duplicate public resource, template, and prompt-key rollback cases plus the watched malformed/recovery case against a hash-verified Linux frozen executable. The pinned artifact was built from synthetic merge `bf4f7dd1`; its Git build-source tree matches candidate `f7c6ed61` tree `6cb691b4`, and the workflow records both source identities. Until an uploaded workflow receipt reports all four expected cases passing, this remains pending acceptance. Its managed fixtures pin Python 3.12, uv 0.9.26, and actions-core 1.0.2; each case checks the actual frozen parent and the managed worker's interpreter and Core origin. This proof is separate from source-mode pytest and the real-RCC provider rollback workflow.

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
