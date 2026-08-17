# Install Community Design

## Goal

Replace the developer-only `BuildCommunity` task with `InstallCommunity`, which
builds, validates, and installs the community Action Server executable into the
location already selected by the caller's `PATH`.

## Installation contract

The task retains the existing frontend build, Go-wrapped executable build, and
pre-install `new --help` smoke test. It then resolves `action-server` with
`shutil.which`. When an executable already resolves, that file is the install
target. When none resolves, the task selects the platform user-local executable
directory and requires that directory to be present on `PATH`.

Installation uses a temporary file in the target directory followed by an
atomic replace. This keeps the previous executable intact if copying fails and
avoids exposing a partial binary. POSIX executable permissions are preserved.
The task never elevates privileges; an unwritable target fails with the target
path and recovery guidance.

After replacement, the task runs the installed executable's `version` and
`new --help` commands. A task succeeds only when the built artifact and installed
artifact both pass their smoke checks.

## Public surface

`developer/toolkit.yaml` exposes `InstallCommunity`; `BuildCommunity` and the
`build-community` dispatcher command are removed. The Python dispatcher exposes
`install-community`. README, CI/workflow contracts, toolkit tests, and canonical
repository guidance use the new name and describe the installation behavior.

## Failure behavior

The task fails without altering the existing executable when the build or
pre-install smoke test fails. Target resolution, directory creation, copying,
atomic replacement, and post-install validation failures report the relevant
path. No broad PATH mutation, package-manager operation, or privileged write is
attempted.

## Verification

Focused toolkit tests cover existing-target resolution, no-target fallback,
unwritable or invalid targets, atomic replacement, command wiring, and both
post-install smoke checks. The repository toolkit test gate and documentation
contracts must pass. A real developer run must prove that `command -v
action-server` resolves to the installed artifact and that the installed
commands succeed.

## Separate lifecycle defect

This task does not mask or claim to repair the independently observed Action
Server lifecycle defect: after its launching terminal disappeared, an orphaned
server retained listening sockets, its preload workers became zombies, CPU use
rose, and HTTP requests stopped receiving responses. That defect requires a
deterministic regression test and root-cause-specific change before any fix.
