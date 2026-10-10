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

For a one-time start, pass each package directory to the same
`action-server start --actions-sync=true` invocation. The directories form
one desired set: actions from every directory are synchronized together, and
the result does not depend on argument order. If admission of any directory
fails, the previous database catalog is kept.

Use separate `import` commands followed by `start --actions-sync=false` when
you want to add packages to the database without synchronizing a complete
desired set on each start.

Example:

```
action-server import --dir=<path to action-package 1> --datadir=<path to datadir>
action-server import --dir=<path to action-package 2> --datadir=<path to datadir>
action-server start --actions-sync=false --datadir=<path to datadir>
```

Important: in this mode, each new import will add new actions to the database.
If at some point some action needs to be removed, it's possible to use the
`action-server datadir clear-actions` command to remove all actions from the database
and then re-import the actions again.

For packages without a managed environment, action code is loaded from the
package directory at execution time. A failed synchronization can preserve
the prior database catalog without preserving the prior source files: calls
may execute edits made before the failed synchronization, or fail if the
current source is invalid. Restore the last-good source before retrying when
you need the last-good behavior.

Example:

```
action-server datadir clear-actions --datadir=<path to datadir>
action-server import --dir=<path to action-package 1> --datadir=<path to datadir>
action-server import --dir=<path to action-package 2> --datadir=<path to datadir>
action-server start --actions-sync=false --datadir=<path to datadir>
```
