<!-- markdownlint-disable -->

# module `actions.cli`

# Functions

______________________________________________________________________

## `main`

Entry point for running actions from actions-core.

**Args:**

- <b>`args`</b>: The command line arguments.

- <b>`exit`</b>: Determines if the process should exit right after executing the command.

- <b>`plugin_manager`</b>: Provides a way to customize internal functionality (should not be used by external clients in general).

**Returns:**
The exit code for the process.

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/cli.py#L18)

```python
main(
    args=None,
    exit: bool = True,
    plugin_manager: Optional[ForwardRef('_PluginManager')] = None
) → int
```
