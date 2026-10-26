<!-- markdownlint-disable -->

# module `actions.data`

Read declared, eagerly prepared logical data in a trusted Action execution.

This API performs no query, network request, credential lookup or file access. The trusted Runtime must explicitly install a verified execution context first.

# Functions

______________________________________________________________________

## `scan`

Return fresh rows from one declared eager scan in the current execution.

Optional null fields are omitted. No parameters, lazy queries or writes are supported. An absent context or undeclared lookup raises ValueError.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/data/_context.py#L282)

```python
scan(requirement_id: 'str', operation: 'str') → list[dict[str, Scalar]]
```
