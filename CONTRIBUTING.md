# Contributing

This guide covers `joshyorko/actions` on the `community` branch. Start with the
[RCC developer workflow](#rcc-developer-setup) before package or frontend work.

## Frontend Development

### Building the Frontend

The Action Server frontend uses the public dependencies declared in its package
manifest and lockfile.

#### Prerequisites

Use the RCC toolchain in `developer/setup.yaml` (Node.js 20.19.3), or the
repository Dev Container (Node.js 22). The frontend requires Node.js >=20.19.0.
The commands below run in that prepared environment, not an ad hoc host install.

#### Build Steps

```bash
cd action_server/frontend
npm ci          # Install dependencies (no credentials needed!)
npm run build:runtime
npm run build:canvas
```

#### Development Mode

```bash
npm run dev     # Start development server with hot reload
npm run test:quality
```

Frontend dependency updates are made in `action_server/frontend/package.json`
and its lockfile, then verified with the runtime and Canvas builds.

## Libraries

### RCC developer setup

RCC is the cross-platform developer gateway. It supplies the isolated toolchain and
dispatches package commands to Poetry and Invoke; Poetry remains authoritative for each
package's dependencies and lockfile.

Use [Josh's RCC fork](https://github.com/joshyorko/rcc) **v18.19.3**, the primary
pin in `developer/toolkit.py` and `.github/workflows/developer_toolkit.yml`.
**v18.18.1 is N−1 compatibility only**; its CI lane explicitly sets
`ACTIONS_TOOLKIT_EXPECTED_RCC_VERSION=v18.18.1`. Do not use upstream `latest`
or override the expected version to bypass a mismatch.

Run Doctor → Bootstrap → verification from the repository root:

```bash
rcc run -r developer/toolkit.yaml --dev -t Doctor
rcc run -r developer/toolkit.yaml --dev -t Bootstrap
rcc run -r developer/toolkit.yaml --dev -t ToolkitTest
```

If RCC is not installed, use the repository launchers with explicit task names. On Linux and
macOS the shell launcher prefers the `joshyorko/tools/rcc` Homebrew cask when Brew is
available, then falls back to the pinned Josh RCC release asset:

```bash
./devutils/bin/develop.sh Doctor
./devutils/bin/develop.sh Bootstrap
./devutils/bin/develop.sh ToolkitTest
```

On Windows, run `devutils\bin\develop.bat Doctor`, then `Bootstrap`, then
`ToolkitTest`. Both launchers default to Bootstrap when no task is supplied.

Cloud agents must read [AGENTS.md](AGENTS.md) and
[the repository skill](.agents/skills/actions-repository/SKILL.md). RCC owns the
outer toolchain; Poetry owns package dependencies and committed lockfiles. Do
not install host Poetry/pip tooling to work around a failed toolkit task.

### Development

To start working on a library, bootstrap all package environments through RCC from the
repository root:

```
rcc run -r developer/toolkit.yaml --dev -t Bootstrap
```

The toolkit runs package-local Poetry environments inside RCC and never requires a host
virtual-environment activation.

### Calling toolkit tasks

Run toolkit tasks from the repository root:

For instance, linting can be run with:

```
rcc run -r developer/toolkit.yaml --dev -t Lint
```

Run the focused gateway contracts with:

```
rcc run -r developer/toolkit.yaml --dev -t ToolkitTest
```

Run the combined static and portable Python test gate with:

```
rcc run -r developer/toolkit.yaml --dev -t CheckAll
```

Type-checking can be checked with:

```
rcc run -r developer/toolkit.yaml --dev -t Typecheck
```

Docs should be generated after each change with:

```
rcc run -r developer/toolkit.yaml --dev -t Docs
```

### Testing

The toolkit's `Test` task runs the portable Python gates. It excludes Work Items
`persistent_backend_service` tests and Action Server integration tests.
`FrontendTest` runs `npm ci` and the full `npm run test` suite; it is separate
from the frontend shipping quality/build gates. See
[build and verification boundaries](docs/BUILD_INSTRUCTIONS.md) before choosing
a gate. `ToolkitTest` alone does not prove package, frontend, or service acceptance.

> It's recommended that you configure your favorite editor/IDE to use the test framework inside your IDE.

### Releasing

To make a new release for a library, ensure the following steps are accomplished in order:

1. Documentation is up-to-date through the toolkit's `Docs` task and `CheckAll` is passing.
2. The version is bumped according to [semantic versioning](https://semver.org/). This can be done by running
   `inv set-version <version>`, which updates all relevant files with the new version number, then adds an entry to the
   _docs/CHANGELOG.md_ describing the changes.
3. The changes above are already committed/integrated into `master`, the test workflows in GitHub Actions are passing,
   and you're operating on the `master` branch locally.
4. You run `inv make-release` to create and push the release tag which will trigger the GitHub workflow that makes the
   release.

> To trigger a release, a commit should be tagged with the name and version of the library. The tag can be generated
> and pushed automatically with `inv make-release`. After the tag has been pushed, a corresponding GitHub Actions 
> workflow will be triggered that builds the library and publishes it to PyPI.
