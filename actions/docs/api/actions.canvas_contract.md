<!-- markdownlint-disable -->

# module `actions.canvas_contract`

Public authoring contract for safe, declarative Action Canvas views.

# Variables

- **CanvasNode**
- **CanvasNodeV2**
- **CanvasBindingId**

# Functions

______________________________________________________________________

## `parse_canvas_spec`

Parse bounded JSON and dispatch only an explicitly supported version.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L356)

```python
parse_canvas_spec(raw: 'str | bytes | bytearray') → CanvasSpec | CanvasSpecV2
```

______________________________________________________________________

## `validate_canvas_spec`

Validate either explicit version without upgrading retained documents.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L363)

```python
validate_canvas_spec(document: 'object') → CanvasSpec | CanvasSpecV2
```

______________________________________________________________________

# Class `CanvasArtifact`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

______________________________________________________________________

# Class `CanvasCard`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

______________________________________________________________________

# Class `CanvasChart`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

______________________________________________________________________

# Class `CanvasForm`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

## Methods

______________________________________________________________________

### `unique_field_names`

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L78)

```python
unique_field_names() → CanvasForm
```

______________________________________________________________________

# Class `CanvasFormField`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

______________________________________________________________________

# Class `CanvasInspector`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

## Methods

______________________________________________________________________

### `unique_field_keys`

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L180)

```python
unique_field_keys() → CanvasInspector
```

______________________________________________________________________

# Class `CanvasLog`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

______________________________________________________________________

# Class `CanvasSpec`

Closed v1 reader; its canonical serialization is unchanged.

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

## Methods

______________________________________________________________________

### `from_json`

Parse bounded JSON, reject duplicate keys, then validate the spec.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L284)

```python
from_json(raw: 'str | bytes | bytearray') → _Spec
```

______________________________________________________________________

### `from_python`

Build from Python field names while keeping JSON validation alias-only.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L321)

```python
from_python(values: 'object') → _Spec
```

______________________________________________________________________

### `to_json`

Return canonical UTF-8 JSON bytes represented as a string.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L331)

```python
to_json() → str
```

______________________________________________________________________

### `validate_tree_and_bindings`

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L232)

```python
validate_tree_and_bindings(self: '_Spec') → _Spec
```

______________________________________________________________________

# Class `CanvasSpecV2`

Explicit v2 reader adding bounded card, chart, log and inspector syntax.

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

## Methods

______________________________________________________________________

### `from_json`

Parse bounded JSON, reject duplicate keys, then validate the spec.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L284)

```python
from_json(raw: 'str | bytes | bytearray') → _Spec
```

______________________________________________________________________

### `from_python`

Build from Python field names while keeping JSON validation alias-only.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L321)

```python
from_python(values: 'object') → _Spec
```

______________________________________________________________________

### `to_json`

Return canonical UTF-8 JSON bytes represented as a string.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L331)

```python
to_json() → str
```

______________________________________________________________________

### `validate_tree_and_bindings`

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L232)

```python
validate_tree_and_bindings(self: '_Spec') → _Spec
```

______________________________________________________________________

# Class `CanvasStack`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

______________________________________________________________________

# Class `CanvasStackV2`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

______________________________________________________________________

# Class `CanvasStatus`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

______________________________________________________________________

# Class `CanvasTable`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

## Methods

______________________________________________________________________

### `unique_column_keys`

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/canvas_contract/_models.py#L102)

```python
unique_column_keys() → CanvasTable
```

______________________________________________________________________

# Class `CanvasTableColumn`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

______________________________________________________________________

# Class `CanvasText`

## Properties

- `model_extra`

Get extra fields set during validation.

**Returns:**
A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.

- `model_fields_set`

Returns the set of fields that have been explicitly set on this model instance.

**Returns:**
A set of strings representing the fields that have been set, i.e. that were not filled from defaults.

# Exceptions

______________________________________________________________________

## `CanvasSpecValidationError`

A CanvasSpec document violates the versioned authoring contract.
