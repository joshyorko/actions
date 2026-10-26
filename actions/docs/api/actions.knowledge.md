<!-- markdownlint-disable -->

# module `actions.knowledge`

Select bounded Knowledge results prepared by the trusted Runtime.

These functions do not query providers or read files, environment or credentials. An ingestion result describes staged work; only canonical Run completion proves publication. Search arguments must match the exact host-prepared invocation.

# Functions

______________________________________________________________________

## `ingest`

Return a fresh prepared ingestion result, not publication authority.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/knowledge/__init__.py#L10)

```python
ingest(requirement_id: str, operation: str) → dict
```

______________________________________________________________________

## `search`

Return the prepared search result only when every parameter matches.

The Runtime validates handle authority and provider-specific bounds. Changing arguments here cannot perform another search or access another corpus.

[**Link to source**](https://github.com/joshyorko/actions/blob/community/actions/src/actions/knowledge/__init__.py#L15)

```python
search(
    requirement_id: str,
    operation: str,
    ingestion_handle: str,
    query: str,
    offset: int = 0,
    limit: int = 20
) → dict
```
