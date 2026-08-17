# Contributing

This is a contribution guide for the Sema4ai actions and action server projects and its associated libraries.

## Frontend Development

### Building the Frontend

The Action Server frontend uses vendored design system packages to enable builds without private registry credentials.

#### Prerequisites

- **Node.js**: LTS 20.x (20.9.0 or later)
- **npm**: 10.x or later

#### Build Steps

```bash
cd action_server/frontend
npm ci          # Install dependencies (no credentials needed!)
npm run build   # Build the frontend
```

#### Development Mode

```bash
npm run dev     # Start development server with hot reload
npm test        # Run tests
npm run test:lint   # Run linter
npm run test:types  # Run TypeScript type checking
```

### Vendored Dependencies

The frontend uses three vendored design system packages located in `action_server/frontend/vendored/`:

- **@sema4ai/components** - UI component library
- **@sema4ai/icons** - Icon library
- **@sema4ai/theme** - Theming system

These packages are vendored (copied into the repository) to enable external contributors to build without authentication to private GitHub Packages.

#### For Maintainers: Updating Vendored Packages

If you have access to Sema4.ai's GitHub Packages, you can update vendored packages:

1. **Authenticate to GitHub Packages**:
   ```bash
   export GITHUB_TOKEN="your_github_token"
   echo "//npm.pkg.github.com/:_authToken=$GITHUB_TOKEN" > ~/.npmrc
   echo "@sema4ai:registry=https://npm.pkg.github.com" >> ~/.npmrc
   ```

2. **Update a package**:
   ```bash
   cd action_server
   python build-binary/vendor-frontend.py \
     --package @sema4ai/components \
     --version 0.1.2
   ```

3. **Verify integrity**:
   ```bash
   python -m pytest tests/action_server_tests/test_vendored_integrity.py -v
   ```

4. **Test the build**:
   ```bash
   cd frontend
   npm ci && npm run build
   ```

5. **Commit the changes**:
   ```bash
   git add vendored/ package.json
   git commit -m "chore: Update vendored packages"
   ```

#### Automated Updates

Automated monthly update checks were removed from the community branch because they require access to private `@sema4ai/*` packages.
Package updates are handled manually by maintainers with GitHub Packages access.

For more details, see the [vendored packages documentation](action_server/frontend/vendored/README.md).

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
