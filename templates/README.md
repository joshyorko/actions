# Action Templates

These community templates help you create Python action packages for the [Actions Runtime](../README.md#quickstart) and its Action Server. See the [Action Server guide](../action_server/README.md) and [Actions library guide](../actions/README.md) for current product documentation.

## Quickstart

Follow the [Actions Runtime quickstart](../README.md#quickstart) to install the server, create a project, and run it.

## Dependency management

Add project dependencies to its `package.yaml` file.

See the [package.yaml guide](../action_server/docs/guides/01-package-yaml.md) for environment and dependency configuration.

Use any editor for the generated Python project. Run and test actions through the Action Server using the instructions in the [quickstart](../README.md#quickstart).

## Focused examples

- [Canvas mail and chat](canvas-mail-chat/README.md) is a standalone, offline
  MCP Apps example. It renders synthetic email and chat previews from one
  shared message model and returns the same records as plain text for clients
  that do not display the Canvas resource.
