<!-- markdownlint-disable -->

# module `actions.internal_runtime`

Internal asynchronous child Run operations explicitly delegated by Runtime.

The Runtime must install a trusted local transport for the current Action. These calls do not use HTTP/MCP and do not themselves grant discovery, execution, result-read, or cancellation authority. There is deliberately no wait operation and no API for selecting a parent Run or worker.

# Functions

______________________________________________________________________

## `cancel_child_run`

Request cancellation; `cancel_pending` is not terminal confirmation.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/internal_runtime/__init__.py#L151)

```python
cancel_child_run(handle: 'ChildRunHandle') → ChildRunStatus
```

______________________________________________________________________

## `child_run_status`

Read lifecycle and host-authorized result references, never raw output.

References are opaque and do not grant later reads; Runtime must reauthorize each follow-up access.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/internal_runtime/__init__.py#L137)

```python
child_run_status(handle: 'ChildRunHandle') → ChildRunStatus
```

______________________________________________________________________

## `submit_child_run`

Admit one delegated child asynchronously and return its opaque handle.

`binding` names a host-declared delegation. `key` is supplied by the Action and must be stable for the same logical child call across parent retries. Runtime scopes it to the parent Run and binding and rejects conflicting payloads. It is an idempotency label, not an authorization token.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/internal_runtime/__init__.py#L115)

```python
submit_child_run(
    binding: 'str',
    key: 'str',
    inputs: 'Mapping[str, object]'
) → ChildRunHandle
```

______________________________________________________________________

# Class `ChildResultReference`

Opaque, metadata-only result reference supplied by an authorized host.

The handle is a reference, not a bearer grant. Runtime must reauthorize any later read; raw result bytes are never carried in this value.

### `__init__`

```python
__init__(
    handle: 'str',
    name: 'str',
    media_type: 'str',
    size_bytes: 'int',
    digest: 'str | None' = None
) → None
```

______________________________________________________________________

# Class `ChildRunHandle`

Opaque child Run reference; possession grants no read or cancel access.

### `__init__`

```python
__init__(id: 'str') → None
```

______________________________________________________________________

# Class `ChildRunStatus`

Bounded lifecycle plus authorized result references, never raw bytes.

### `__init__`

```python
__init__(
    handle: 'ChildRunHandle',
    state: 'ChildRunState',
    result_references: 'tuple[ChildResultReference, ]' = ()
) → None
```

# Exceptions

______________________________________________________________________

## `ChildRunContractError`

The Action supplied an invalid or unbounded child operation.

______________________________________________________________________

## `ChildRunUnavailable`

No trusted Runtime transport is installed in this Action context.

# Enums

______________________________________________________________________

## `ChildRunState`

### Values

- **PENDING** = pending
- **RUNNING** = running
- **CANCEL_PENDING** = cancel_pending
- **SUCCEEDED** = succeeded
- **FAILED** = failed
- **CANCELLED** = cancelled
