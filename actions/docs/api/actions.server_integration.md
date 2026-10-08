<!-- markdownlint-disable -->

# module `actions.server_integration`

Versioned Actions Runtime integration contracts.

This module is the narrow Core-to-Runtime integration surface used by the separately distributed `actions-runtime` package. It preserves the existing objects and behavior; it is not a general end-user convenience API.

# Variables

- **DEFAULT_EXCLUSION_PATTERNS**

# Functions

______________________________________________________________________

## `format_lint_results`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_lint_action.py#L461)

```python
format_lint_results(
    lint_result: Union[dict, LintResultTypedDict]
) → Optional[FormattedLintResult]
```

______________________________________________________________________

# Class `EPManagedParameters`

The protocol for a class that describes the managed parameters when calling an action.

## Methods

______________________________________________________________________

### `inject_managed_params`

This enables the addition of managed parameters into a call to the action.

**Args:**

- <b>`sig`</b>: The signature of the function being called.
- <b>`request_contexts`</b>: The request contexts (may be None).
- <b>`new_kwargs`</b>: The new kwargs (where the parameters should be injected).
- <b>`original_kwargs`</b>: The original kwargs passed to the function.

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_customization/_extension_points.py#L44)

```python
inject_managed_params(
    sig: Signature,
    request_contexts: Optional[ForwardRef('RequestContexts')],
    new_kwargs: Dict[str, Any],
    original_kwargs: Dict[str, Any]
) → Dict[str, Any]
```

______________________________________________________________________

# Class `ManagedParameters`

Default implementation of EPManagedParameters.

The idea is that in the constructor it receives the parameter names and the actual instance mapped from the parameter name.

### `__init__`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_managed_parameters.py#L178)

```python
__init__(param_name_to_instance: Dict[str, Any])
```

## Methods

______________________________________________________________________

### `get_managed_param_type`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_managed_parameters.py#L288)

```python
get_managed_param_type(
    param_name: str,
    param: Optional[Parameter] = None,
    node: Optional[FunctionDef] = None
) → type | str
```

______________________________________________________________________

### `get_request_contexts`

Returns the action context or None if the context wasn't really set.

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_managed_parameters.py#L226)

```python
get_request_contexts(
    new_kwargs: Dict[str, Any],
    original_kwargs: Dict[str, Any]
) → Optional[ForwardRef('RequestContexts')]
```

______________________________________________________________________

### `inject_managed_params`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_managed_parameters.py#L251)

```python
inject_managed_params(
    sig: Signature,
    request_contexts: Optional[ForwardRef('RequestContexts')],
    new_kwargs: Dict[str, Any],
    original_kwargs: Dict[str, Any]
) → Dict[str, Any]
```

______________________________________________________________________

### `is_managed_param`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_managed_parameters.py#L194)

```python
is_managed_param(
    param_name: str,
    node: Optional[FunctionDef] = None,
    param: Optional[Parameter] = None
) → bool
```

______________________________________________________________________

# Class `PluginManager`

This is a manager of plugins (which we refer to extension points and implementations). Mostly, we have a number of EPs (Extension Points) and implementations may be registered for those extension points. The PluginManager is able to provide implementations (through #get_implementations) which are not kept on being tracked and a special concept which keeps an instance alive for an extension (through #get_instance).

### `__init__`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_customization/_plugin_manager.py#L86)

```python
__init__() → None
```

## Methods

______________________________________________________________________

### `exit`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_customization/_plugin_manager.py#L253)

```python
exit()
```

______________________________________________________________________

### `get_implementations`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_customization/_plugin_manager.py#L109)

```python
get_implementations(ep: Union[Type, str]) → list
```

______________________________________________________________________

### `get_instance`

Creates an instance in this plugin manager: Meaning that whenever a new EP is asked in the same context it'll receive the same instance created previously (and it'll be kept alive in the plugin manager).

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_customization/_plugin_manager.py#L210)

```python
get_instance(ep: Union[Type, str], context: Optional[str] = None) → Any
```

______________________________________________________________________

### `has_instance`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_customization/_plugin_manager.py#L195)

```python
has_instance(ep: Union[Type, str], context=None)
```

______________________________________________________________________

### `iter_existing_instances`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_customization/_plugin_manager.py#L189)

```python
iter_existing_instances(ep: Union[Type, str])
```

______________________________________________________________________

### `load_plugins_from`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_customization/_plugin_manager.py#L93)

```python
load_plugins_from(directory: Path) → int
```

______________________________________________________________________

### `register`

:param ep: :param str impl: This is the full path to the class implementation.:param kwargs: :param context: If keep_instance is True, it's possible to register it for a givencontext.:param keep_instance: If True, it'll be only available through pm.get_instance and theinstance will be kept for further calls.If False, it'll only be available through get_implementations.

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_customization/_plugin_manager.py#L122)

```python
register(
    ep: Type,
    impl,
    kwargs: Optional[dict] = None,
    context: Optional[str] = None,
    keep_instance: bool = False
)
```

______________________________________________________________________

### `set_instance`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_customization/_plugin_manager.py#L179)

```python
set_instance(ep: Type, instance, context=None) → None
```

______________________________________________________________________

### `unregister`

[**Link to source**](https://github.com/sema4ai/actions/tree/master/actions/src/actions/_customization/_plugin_manager.py#L168)

```python
unregister(ep: Type, context: Optional[str] = None, keep_instance: bool = False)
```
