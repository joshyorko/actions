# Contributing

This is a contribution guide for the Sema4ai actions and action server projects and its associated libraries.

## Frontend Development

### Building the Frontend

The Action Server frontend uses the public dependencies declared in its package
manifest and lockfile.

#### Prerequisites

- **Node.js**: 22.x
- **npm**: 10.x or later

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

### Prerequisites

RCC is the cross-platform developer gateway. It supplies the isolated toolchain and
dispatches package commands to Poetry and Invoke; Poetry remains authoritative for each
package's dependencies and lockfile.

Install RCC v18.18.1, then run from the repository root:

```bash
rcc run -r developer/toolkit.yaml --dev -t Doctor
rcc run -r developer/toolkit.yaml --dev -t Bootstrap
```

If RCC is not installed, the repository launchers run `Bootstrap` directly. On Linux and
macOS the shell launcher prefers the `joshyorko/tools/rcc` Homebrew cask when Brew is
available, then falls back to the pinned Josh RCC release asset:

```bash
./devutils/bin/develop.sh
```

On Windows, run `devutils\bin\develop.bat`. Pass another toolkit task name, such as
`Doctor`, as the first argument when bootstrap is not required.

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

Run the complete static and test gate with:

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

And everything combined with:

```
rcc run -r developer/toolkit.yaml --dev -t CheckAll
```

### Testing

Testing is done with `pytest` for the Python libraries. For javascript `jest` is the used one.

Run the complete Python suite with the toolkit's `Test` task. Frontend tests are
available through `rcc run -r developer/toolkit.yaml --dev -t FrontendTest`.

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
