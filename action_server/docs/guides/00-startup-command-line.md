# Serving Actions with the Action Server

The action server's main purpose is managing the lifecycle of actions in
an action package.

There are a number of customizations available which make it flexible to
work and manage which actions should be executed. The guide shows a few
of these use-cases below.

## Serving actions from the current directory

The simplest case is just starting the action server at a given folder
with:

```
action-server start
```

In this case, the action server will search recursively for all the Actions
marked as `@action` in files named as `*action*.py` and then it'll start
serving such actions. Any `@action` which
is no longer found from a previous run will be disabled.

All the settings and data related to this run will be stored a folder
located in a directory in `~/robocorp/.action_server` (or
`%LOCALAPPDATA%/robocorp/.action_server` in windows) which is automatically
computed based on the current directory location.

It's possible to customize the directory by using the `--datadir` flag.

Example:

```
action-server start --datadir=<path to datadir>
```

## Serving actions from multiple directories

One Runtime can serve packages imported into a shared datadir. Additive
imports retain packages and actions omitted from the command:

```bash
action-server import --dir=/packages/a --datadir=/shared/catalog
action-server import --dir=/packages/b --datadir=/shared/catalog
action-server start --actions-sync=false --datadir=/shared/catalog
```

Each package must have a distinct identity (`name` in `package.yaml`, or its
directory name for an unmanaged package). To explicitly reconcile removals,
pass the complete desired set using the existing repeatable `--dir` option:

```bash
action-server start --actions-sync=true --datadir=/shared/catalog \
  --dir=/packages/a --dir=/packages/b
```

Runtime collects and validates every selected package before admitting the
catalog in one database transaction. It disables removed actions within each
selected package and capabilities belonging to omitted packages. Argument
order does not choose the winning package. A failed candidate retains the
previous catalog and admitted package sources; deleting the datadir is not
required for normal reconciliation.

An additive reimport may update or add actions, but it cannot remove an
enabled action while retaining that action's old catalog record. Such an
import is rejected with the prior package intact. Use the complete desired-set
command above to remove capabilities deliberately.

Runtime preserves admitted package files in service-owned source snapshots.
These exclude Runtime databases, credentials, logs and artifacts when the
datadir is inside the package. With `--datadir` equal to the package directory,
Runtime-owned names and configured database/artifact paths are reserved for
Runtime state. Metadata collection that alters the selected source is rejected.
Old snapshots are retained for admitted work; automatic lease-safe collection
is not implemented.

Package-internal `pythonpath` entries use the selected snapshot. Explicit
external `pythonpath` entries retain their original location, including
relative paths outside the package; those external files are mutable and are
not covered by last-good package-source preservation. Generated Python remains
trusted developer code. Source snapshots do not sandbox it or reverse changes
to business data or external services.

HTTP routes remain package-qualified. A unique action keeps its unqualified
OpenAPI operation ID and MCP tool name; name collisions require deterministic
qualification. Adding or removing a conflicting package can therefore change
advertised names. Clients must rediscover the catalog after its revision
changes; an old name is not a durable alias. Disabled actions and whitelists
still apply. These import/synchronization operations do not implement dynamic
Package Revision or Deployment management.
